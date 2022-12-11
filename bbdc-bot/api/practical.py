from datetime import date
from typing import Awaitable, Callable

from ..logger import logger
from .models import BASE_URL, BaseAPI, BBDCSession, Slot, SlotType


class PracticalAPI(BaseAPI):
    slot_type = SlotType.Practical

    async def slot_finder(
        self, session: BBDCSession, want_month: str
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
                    slot_startTime = raw_slot["startTime"]
                    slot_endTime = raw_slot["endTime"]

                    slots[slot_id] = Slot(
                        self.slot_type,
                        slot_day,
                        slot_session,
                        slot_startTime,
                        slot_endTime,
                    )
            return slots

    async def slot_booker(
        self,
        session: BBDCSession,
        found_slots: dict[str, Slot],
        booking_slots: dict[str, Slot],
        on_success: Callable[[Slot], Awaitable[None]],
        on_failure: Callable[[Slot], Awaitable[None]],
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
                await on_success(booked_slot)

            for failed_booking in booking_slots.values():
                logger.info(f"Booking failed: {failed_booking} for {session.user}")
                await on_failure(failed_booking)
