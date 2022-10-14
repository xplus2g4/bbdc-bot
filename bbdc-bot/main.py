import asyncio
from datetime import date, datetime

import aiohttp
import attrs
from bs4 import BeautifulSoup, Tag
from parse import Result, compile, search

from .config import load_config
from .telegram import send_message

BASE_URL = "http://www.bbdc.sg/bbdc"


@attrs.frozen()
class Slot:
    day: date
    session: int
    value: int


async def login(session: aiohttp.ClientSession, username: str, password: str):
    url = f"{BASE_URL}/bbdc_web/header2.asp"
    data = {
        "txtNRIC": username,
        "txtpassword": password,
        "btnLogin": "ACCESS TO BOOKING SYSTEM",
    }
    async with session.get(url, data=data) as r:
        pass


async def get_acc_id(session: aiohttp.ClientSession):
    url = f"{BASE_URL}/b-3c-pLessonBooking1.asp?limit=pl"

    async with session.get(url) as r:
        html_doc = await r.text()
        soup = BeautifulSoup(html_doc, "html.parser")
        acc_id_field = soup.find("input", {"name": "accId"})
        if not isinstance(acc_id_field, Tag):
            raise ValueError("accId not found")
        value = acc_id_field.get("value")
        if not isinstance(value, str):
            raise ValueError("accId value not found")
        return value


async def get_slots(
    session: aiohttp.ClientSession,
    accId: str,
    want_months: list[str],
    want_sessions: list[int],
):
    url = f"{BASE_URL}/b-3c-pLessonBooking1.asp"

    data = aiohttp.FormData()
    data.add_field("accId", accId)
    data.add_field("defPLVenue", 1)
    data.add_field("optVenue", 1)
    for session_no in want_sessions:
        data.add_field("Session", session_no)
    for month in want_months:
        data.add_field("Month", month)
    for i in range(7):
        data.add_field("Day", i + 1)

    async with session.post(url, data=data) as r:
        html_doc = await r.text()
        soup = BeautifulSoup(html_doc, "html.parser")

        p = compile('doTooltipV{}"{day:d}/{month:d}/{year:d}{}","{session:d}"{}')
        slots: list[Slot] = []
        for slot_raw in soup.find_all(type="checkbox"):
            slot_value = int(slot_raw.get("value"))
            slot_info = p.parse(slot_raw.parent.get("onmouseover"))
            if not isinstance(slot_info, Result):
                continue
            slots.append(
                Slot(
                    date(slot_info["year"], slot_info["month"], slot_info["day"]),
                    slot_info["session"],
                    slot_value,
                )
            )
        return slots


async def book_slot(session: aiohttp.ClientSession, acc_id: str, slot_value: int):
    url = f"{BASE_URL}/b-3c-pLessonBookingDetails.asp"

    data = aiohttp.FormData()
    data.add_field("accId", acc_id)
    data.add_field("slot", slot_value)
    async with session.post(url, data=data) as r:
        html_doc = await r.text()
        soup = BeautifulSoup(html_doc, "html.parser")
        msgs = soup.find_all("td", {"class": "errtblmsg"})
        for msg in msgs:
            if not isinstance(msg, Tag):
                return False
            if search("Booking Confirmed !", msg.get_text()) != None:
                return True
        return False


async def main(config):
    headers = {
        "content-type": "application/x-www-form-urlencoded",
    }
    username = config["bbdc"]["username"]
    password = config["bbdc"]["password"]
    want_sessions = config["booking"]["want_sessions"]
    want_months = config["booking"]["want_months"]
    want_dates = [date.fromisoformat(d) for d in config["booking"]["want_dates"]]

    success = False
    msg = ""
    async with aiohttp.ClientSession(headers=headers) as session:
        await login(session, username, password)
        acc_id = await get_acc_id(session)
        slots = await get_slots(
            session,
            acc_id,
            want_months,
            want_sessions,
        )

        for slot in slots:
            if slot.day not in want_dates:
                continue
            success = await book_slot(session, acc_id, slot.value)
            msg = (
                f"[Booking Confirmed]:\nDate: {slot.day.isoformat()}\nSession: {slot.session}"
                if success
                else ""
            )
    if success:
        print(f"{datetime.now()}: Slot Found!")
        print(f"  {msg}")
        await send_message(session, msg)
        loop = asyncio.get_event_loop()
        loop.stop()
    else:
        print(f"{datetime.now()}: No Slot Found")


def app():
    config = load_config()
    interval = config["interval"]

    loop = asyncio.get_event_loop()

    async def periodic():
        while True:
            await main(config)
            await asyncio.sleep(interval * 60)

    loop.run_until_complete(periodic())
