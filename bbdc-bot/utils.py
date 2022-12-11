from .api.models import BaseAPI, BBDCSession, Slot, User, SlotType
from .logger import logger
from .telegram import broadcast_message, private_message


def generate_booking_success_callback(session: BBDCSession):
    async def callback(slot: Slot):
        await private_message(
            session,
            session.user.chat_id,
            f"Booking success: {slot}",
        )

    return callback


def generate_booking_failure_callback(session: BBDCSession):
    async def callback(slot: Slot):
        await private_message(
            session,
            session.user.chat_id,
            f"Booking failed: {slot}",
        )

    return callback


async def find_and_book(session: BBDCSession, api: BaseAPI, query_months: list[str]):
    slots: dict[str, Slot] = {}

    for month in query_months:

        month_slots = await api.slot_finder(
            session,
            month,
        )
        for id, slot in month_slots.items():
            logger.info(f"Slot Found: {slot}")
            slots[id] = slot

    if len(slots) == 0:
        logger.info("No Slot Found")
    else:
        remaining_slots = await _try_booking(
            session.user, session.course_type, api, slots
        )
        if len(remaining_slots) != 0:
            msg = "Slot found:\n" + "\n".join(
                [str(slot) for slot in remaining_slots.values()]
            )
            await broadcast_message(session, msg)


async def _try_booking(
    user: User,
    course_type: str,
    api: BaseAPI,
    slots: dict[str, Slot],
):
    remaining_slots = slots.copy()

    if user.preferred_slots == 0:
        return remaining_slots

    booking_slots: dict[str, Slot] = {}
    for slot_id, found_slot in remaining_slots.items():
        if found_slot in user.preferred_slots:
            booking_slots[slot_id] = found_slot

    if len(booking_slots) == 0:
        return remaining_slots

    async with (await BBDCSession.create(user, course_type)) as session:
        # book_slots removes booked slot from remaining slot
        await api.slot_booker(
            session,
            remaining_slots,
            booking_slots,
            generate_booking_success_callback(session),
            generate_booking_failure_callback(session),
        )

    return remaining_slots
