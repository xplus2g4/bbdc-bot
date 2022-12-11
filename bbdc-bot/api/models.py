import http
from abc import ABC, abstractmethod
from datetime import date
from typing import Awaitable, Callable
from enum import Enum

import aiohttp
import attrs

BASE_URL = "https://booking.bbdc.sg/bbdc-back-service/api"


class SlotType(Enum):
    Practical = "Practical"


@attrs.frozen()
class Slot:
    slot_type: SlotType
    day: date
    session: int
    startTime: str
    endTime: str

    @classmethod
    def createWithInferredTime(
        cls, slot_type: SlotType, day: date, session: int
    ) -> "Slot":
        match session:
            case 1:
                startTime = "07:30"
                endTime = "09:10"
            case 2:
                startTime = "09:20"
                endTime = "11:00"
            case 3:
                startTime = "11:30"
                endTime = "13:10"
            case 4:
                startTime = "13:20"
                endTime = "15:00"
            case 5:
                startTime = "15:20"
                endTime = "17:00"
            case 6:
                startTime = "17:10"
                endTime = "18:50"
            case 7:
                startTime = "19:20"
                endTime = "21:00"
            case 8:
                startTime = "21:10"
                endTime = "22:50"
            case _:
                raise ValueError("Invalid session")
        return cls(slot_type, day, session, startTime, endTime)

    def __repr__(self) -> str:
        return f"date: {self.day.isoformat()}, session: {self.session} ({self.timing})"

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Slot):
            return False
        return (
            self.slot_type == __o.slot_type
            and self.day == __o.day
            and self.session == __o.session
        )

    @property
    def timing(self) -> str:
        return f"{self.startTime}-{self.endTime}"


class User:
    username: str
    password: str
    chat_id: str

    # TODO save preferred slots locally after sucessful booking.
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
                slot_type = SlotType[raw_slot["slot_type"]]
                day = date.fromisoformat(raw_slot["date"])
                sessions = raw_slot["sessions"]
                for s in sessions:
                    preferred_slots.append(
                        Slot.createWithInferredTime(slot_type, day, s)
                    )
            self.preferred_slots = preferred_slots

    def __repr__(self) -> str:
        return self.username


class BBDCSession(aiohttp.ClientSession):
    user: User
    course_type: str

    @classmethod
    async def create(cls, user: User, course_type: str) -> "BBDCSession":
        # Get auth tokens
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(verify_ssl=False)
        ) as session:
            bearer_token = await BBDCSession._get_bearer_token(session, user)
            jsessionid = await BBDCSession._get_jsessionid(
                session, user, bearer_token, course_type
            )

        self = BBDCSession(
            connector=aiohttp.TCPConnector(verify_ssl=False),
            headers={"Authorization": bearer_token, "JSESSIONID": jsessionid},
        )
        self.user = user
        self.course_type = course_type
        return self

    async def __aenter__(self) -> "BBDCSession":
        return self

    @classmethod
    async def _get_bearer_token(
        cls,
        session: aiohttp.ClientSession,
        user: User,
    ) -> str:
        url = f"{BASE_URL}/auth/login"
        data = {
            "userId": user.username,
            "userPass": user.password,
        }
        async with session.post(url, json=data) as r:
            json_content = await r.json()
            if r.status != http.HTTPStatus.OK:
                raise ValueError(f"Login failed")
            return json_content["data"]["tokenContent"]

    @classmethod
    async def _get_jsessionid(
        cls,
        session: aiohttp.ClientSession,
        user: User,
        bearer_token: str,
        course_type: str,
    ):
        url = f"{BASE_URL}/account/listAccountCourseType"

        async with session.post(url, headers={"Authorization": bearer_token}) as r:
            json_content = await r.json()
            target_course = next(
                filter(
                    lambda course: course["courseType"] == course_type,
                    json_content["data"]["activeCourseList"],
                ),
                None,
            )
            if target_course == None:
                raise ValueError(f"Course type not found for {user}")
            return target_course["authToken"]


class BaseAPI(ABC):
    slot_type: SlotType

    @abstractmethod
    async def slot_finder(
        self,
        session: BBDCSession,
        want_month: str,
    ) -> dict[str, Slot]:
        raise NotImplementedError("Subclasses should implement slot finder")

    @abstractmethod
    async def slot_booker(
        self,
        session: BBDCSession,
        found_slots: dict[str, Slot],
        booking_slots: dict[str, Slot],
        on_success: Callable[[Slot], Awaitable[None]],
        on_failure: Callable[[Slot], Awaitable[None]],
    ):
        raise NotImplementedError("Subclasses should implement slot booker")
