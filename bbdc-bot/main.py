import asyncio
from itertools import cycle
from typing import Iterator

from .api import PracticalAPI
from .api.models import BBDCSession, User
from .config import load_config
from .logger import logger
from .utils import find_and_book

USERS: list[User] = []
USER_POOL: Iterator


async def main(config):

    user = next(USER_POOL)
    logger.info(f">>>>>>> Using: {user.username} >>>>>>>")

    query_months: list[str] = config["query_months"]
    course_type: str = config["course_type"]

    async with (await BBDCSession.create(user, course_type)) as session:
        # Practicals
        practical_api = PracticalAPI()
        await find_and_book(session, practical_api, query_months)

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
