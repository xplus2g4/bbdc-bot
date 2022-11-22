import asyncio
from datetime import date
from itertools import cycle
from typing import Iterator

import aiohttp
import attrs

from .config import load_config
from .logger import logger
from .telegram import broadcast_message, private_message


@attrs.frozen()
class Slot:
    day: date
    session: int

    def __repr__(self) -> str:
        return f"date: {self.day.isoformat()}, session: {self.session}"

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Slot):
            return False
        return self.day == __o.day and self.session == __o.session


class User:
    username: str
    password: str
    chat_id: str
    preferred_slots: list[Slot]

    def __init__(self, raw_user: dict):
        self.username = raw_user["username"]
        self.password = raw_user["password"]
        self.chat_id = raw_user["chat_id"]

        if "preferred_slots" not in raw_user:
            self.preferred_slots = []
        else:
            raw_preferred_slots = raw_user["preferred_slots"]
            preferred_slots: list[Slot] = []
            for raw_slot in raw_preferred_slots:
                day = date.fromisoformat(raw_slot["date"])
                sessions = raw_slot["sessions"]
                for s in sessions:
                    preferred_slots.append(Slot(day, s))
            self.preferred_slots = preferred_slots

    def __repr__(self) -> str:
        return self.username


BASE_URL = "https://booking.bbdc.sg/bbdc-back-service/api"
USERS: list[User] = []
USER_POOL: Iterator


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


async def get_session_id(session: aiohttp.ClientSession):
    url = f"{BASE_URL}/account/listAccountCourseType"

    async with session.post(url) as r:
        json_content = await r.json()
        # TODO: need to return authToken against specific courseType.
        # currently we are sending first course authToken which may break the functionality
        return json_content["data"]["activeCourseList"][0]["authToken"]


async def get_slots(
    session: aiohttp.ClientSession,
    auth_token: str,
    want_month: str,
    course_type: str,
) -> dict[str, Slot]:
    url = f"{BASE_URL}/booking/c3practical/listC3PracticalSlotReleased"

    payload = {
        "courseType": course_type,
        "insInstructorId": "",
        "releasedSlotMonth": want_month,
        "stageSubDesc": "Practical Lesson",
        "subVehicleType": None,
        "subStageSubNo": None,
    }
    headers = {"JSESSIONID": auth_token}
    async with session.post(url, json=payload, headers=headers) as r:
        json_content = await r.json()
        if json_content["code"] != 0:
            return {}
        raw_slots = json_content["data"]["releasedSlotListGroupByDay"]
        if raw_slots == None:
            return {}
        slots: dict[str, Slot] = {}
        for date_str, date_slots in raw_slots.items():
            slot_day = date.fromisoformat(date_str.split()[0])
            for raw_slot in date_slots:
                slot_session = int(raw_slot["slotRefName"].split()[1])
                slot_id = raw_slot["slotId"]
                slots[slot_id] = Slot(slot_day, slot_session)
        return slots


async def book_slots(
    session: aiohttp.ClientSession,
    auth_token: str,
    user: User,
    found_slots: dict[str, Slot],
    booking_slots: dict[str, Slot],
    course_type: str,
):
    """
    Book the booking slots for the user. Successful booking will remove the slot from `found_slots`
    """
    url = f"{BASE_URL}/booking/c3practical/callBookC3PracticalSlot"

    payload = {
        "courseType": course_type,
        "insInstructorId": "",
        "slotIdList": [slot for slot in booking_slots.keys()],
        "subVehicleType": None,
    }

    headers = {"JSESSIONID": auth_token}

    booked_slots: dict[str, Slot] = {}
    async with session.post(url, json=payload, headers=headers) as r:
        json_content = await r.json()
        responses = json_content["data"]["bookedPracticalSlotList"]

        for resp in responses:
            slot_id = resp["c3PsrSlotId"]
            booked_slot = booking_slots[slot_id]
            booked_slots[slot_id] = booked_slot
            del found_slots[slot_id]
            del booking_slots[slot_id]

            user.preferred_slots.remove(booked_slot)

            logger.info(f"Booking success: {booked_slot} for {user}")
            await private_message(
                session,
                user.chat_id,
                f"Booking success: {booked_slot}",
            )

        for failed_booking in booking_slots.values():
            logger.info(f"Booking failed: {failed_booking} for {user}")
            await private_message(
                session,
                user.chat_id,
                f"Booking failed: {failed_booking}\nYou may want to check your balance?",
            )


async def try_booking(course_type: str, slots: dict[str, Slot]):
    global USERS

    remaining_slots = slots.copy()

    for user in USERS:
        if user.preferred_slots == 0:
            continue

        booking_slots: dict[str, Slot] = {}
        for slot_id, found_slot in remaining_slots.items():
            if found_slot in user.preferred_slots:
                booking_slots[slot_id] = found_slot

        if len(booking_slots) == 0:
            continue

        bearer_token = await get_login_token(user.username, user.password)
        headers = {"Authorization": bearer_token}
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(verify_ssl=False), headers=headers
        ) as session:
            session_id = await get_session_id(session)
            # book_slots removes booked slot from remaining slot
            await book_slots(session, session_id, user, remaining_slots, booking_slots, course_type)

    return remaining_slots


async def main(config):

    user = next(USER_POOL)
    logger.info(f">>>>>>> Using: {user.username} >>>>>>>")

    query_months: list[str] = config["query_months"]

    bearer_token = await get_login_token(user.username, user.password)
    headers = {"Authorization": bearer_token}

    slots: dict[str, Slot] = {}
    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(verify_ssl=False), headers=headers
    ) as session:
        session_id = await get_session_id(session)
        for month in query_months:

            month_slots = await get_slots(
                session,
                session_id,
                month,
                config["course_type"],
            )
            for id, slot in month_slots.items():
                logger.info(f"Slot Found: {slot}")
                slots[id] = slot

        if len(slots) == 0:
            logger.info("No Slot Found")
        else:
            remaining_slots = await try_booking(config["course_type"], slots)
            for slot in remaining_slots.values():
                await broadcast_message(
                    session,
                    f"Slot found: {slot}",
                )

    logger.info(f">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\n")


def load_users(config):
    global USERS, USER_POOL

    accounts = config["accounts"]
    for account in accounts:
        USERS.append(User(account))
    USER_POOL = cycle(USERS)


def app():
    config = load_config()
    interval = config["interval"]
    load_users(config)

    loop = asyncio.get_event_loop()

    async def periodic():
        while True:
            await main(config)
            await asyncio.sleep(interval * 60)

    loop.run_until_complete(periodic())
