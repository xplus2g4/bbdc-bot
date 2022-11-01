import asyncio
from datetime import date, datetime

import aiohttp
import attrs
from bs4 import BeautifulSoup, Tag
from parse import Result, compile, search
from urllib.parse import quote_plus

from .config import load_config
from .telegram import send_message

BASE_URL = "https://booking.bbdc.sg/bbdc-back-service/api"


@attrs.frozen()
class Slot:
    day: date
    session: int
    value: int


async def get_login_token(
    username: str,
    password: str,
):
    url = f"{BASE_URL}/auth/login"
    data = {
        "userId": username,
        "userPass": password,
    }
    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(verify_ssl=False)
    ) as session:
        async with session.post(url, json=data) as r:
            json_content = await r.json()
            return json_content["data"]["tokenContent"]


async def get_acc_id(session: aiohttp.ClientSession):
    url = f"{BASE_URL}/account/listAccountCourseType"

    async with session.post(url) as r:
        json_content = await r.json()
        return json_content["data"]["activeCourseList"][0]["accountId"]


async def get_slots(
    session: aiohttp.ClientSession,
    accId: str,
    want_months: list[str],
    want_sessions: list[int],
):
    url = f"{BASE_URL}/booking/c3practical/listC3PracticalSlotReleased"

    payload = {
        "courseType": "3A",
        "insInstructorId": "",
        "releasedSlotMonth": want_months[0],
        "stageSubDesc": "Practical Lesson",
        "subVehicleType": None,
        "subStageSubNo": None,
        "accountId": accId,
    }
    async with session.post(url, json=payload) as r:
        json_content = await r.json()
        if json_content["code"] != 0:
            return []
        raw_slots = json_content["data"]["releasedSlotListGroupByDay"]
        if raw_slots == None:
            return []
        slots: list[Slot] = []
        for date_str, date_slots in raw_slots.items():
            slot_day = date.fromisoformat(date_str.split()[0])
            for raw_slot in date_slots:
                slot_session = int(raw_slot["slotRefName"].split()[1])
                if slot_session in want_sessions:
                    slot_id = raw_slot["slotId"]
                    slots.append(Slot(slot_day, slot_session, slot_id))
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
    username = config["bbdc"]["username"]
    password = config["bbdc"]["password"]
    want_sessions = config["booking"]["want_sessions"]
    want_months = config["booking"]["want_months"]
    want_dates = [date.fromisoformat(d) for d in config["booking"]["want_dates"]]

    bearer_token = await get_login_token(username, password)
    headers = {"Authorization": bearer_token}
    success = False
    msg = ""
    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(verify_ssl=False), headers=headers
    ) as session:
        acc_id = await get_acc_id(session)
        slots = await get_slots(
            session,
            acc_id,
            want_months,
            want_sessions,
        )
        for slot in slots:
            if slot.day in want_dates:
                await send_message(
                    session,
                    f"[Slot found]:\nDate: {slot.day.isoformat()}\nSession: {slot.session}",
                )

        # for slot in slots:
        #     if slot.day not in want_dates:
        #         continue
        #     success = await book_slot(session, acc_id, slot.value)
        #     msg = (
        #         f"[Booking Confirmed]:\nDate: {slot.day.isoformat()}\nSession: {slot.session}"
        #         if success
        #         else ""
        #     )
    if success:
        pass
        # print(f"{datetime.now()}: Slot Found!")
        # print(f"  {msg}")
        # await send_message(session, msg)
        # loop = asyncio.get_event_loop()
        # loop.stop()
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
