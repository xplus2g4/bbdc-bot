import asyncio
from datetime import date
from itertools import cycle
from typing import Iterator

from .config import load_config
from .logger import logger
from .models import BASE_URL, BBDCSession, Slot, User
from .telegram import broadcast_message, private_message

USERS: list[User] = []
USER_POOL: Iterator


async def get_slots(
    session: BBDCSession,
    want_month: str,
) -> dict[str, Slot]:
    url = f"{BASE_URL}/booking/c3practical/listC3PracticalSlotReleased"

    payload = {
        "courseType": session.course_type,
        "insInstructorId": "",
        "releasedSlotMonth": want_month,
        "stageSubDesc": "Practical Lesson",
        "subVehicleType": None,
        "subStageSubNo": None,
    }
    async with session.post(url, json=payload) as r:
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
    session: BBDCSession,
    found_slots: dict[str, Slot],
    booking_slots: dict[str, Slot],
):
    """
    Book the booking slots for the user. Successful booking will remove the slot from `found_slots`
    """
    url = f"{BASE_URL}/booking/c3practical/callBookC3PracticalSlot"

    payload = {
        "courseType": session.course_type,
        "insInstructorId": "",
        "slotIdList": [slot for slot in booking_slots.keys()],
        "subVehicleType": None,
    }

    booked_slots: dict[str, Slot] = {}
    async with session.post(url, json=payload) as r:
        json_content = await r.json()
        responses = json_content["data"]["bookedPracticalSlotList"]

        for resp in responses:
            slot_id = resp["c3PsrSlotId"]
            booked_slot = booking_slots[slot_id]
            booked_slots[slot_id] = booked_slot
            del found_slots[slot_id]
            del booking_slots[slot_id]

            session.user.preferred_slots.remove(booked_slot)

            logger.info(f"Booking success: {booked_slot} for {session.user}")
            await private_message(
                session,
                session.user.chat_id,
                f"Booking success: {booked_slot}",
            )

        for failed_booking in booking_slots.values():
            logger.info(f"Booking failed: {failed_booking} for {session.user}")
            await private_message(
                session,
                session.user.chat_id,
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

        async with (await BBDCSession.create(user, course_type)) as session:
            # book_slots removes booked slot from remaining slot
            await book_slots(session, remaining_slots, booking_slots)

    return remaining_slots


async def main(config):

    user = next(USER_POOL)
    logger.info(f">>>>>>> Using: {user.username} >>>>>>>")

    query_months: list[str] = config["query_months"]
    course_type: str = config["course_type"]

    slots: dict[str, Slot] = {}
    async with (await BBDCSession.create(user, course_type)) as session:
        for month in query_months:

            month_slots = await get_slots(
                session,
                month,
            )
            for id, slot in month_slots.items():
                logger.info(f"Slot Found: {slot}")
                slots[id] = slot

        if len(slots) == 0:
            logger.info("No Slot Found")
        else:
            remaining_slots = await try_booking(session.course_type, slots)
            if len(remaining_slots) != 0:
                msg = "Slot found:\n" + "\n".join(
                    [str(slot) for slot in remaining_slots.values()]
                )
                await broadcast_message(session, msg)

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
