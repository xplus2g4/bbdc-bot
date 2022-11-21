import asyncio
import http
from functools import lru_cache
from urllib.parse import quote_plus

import aiohttp

from .config import load_config
from .logger import logger


async def broadcast_message(session: aiohttp.ClientSession, text: str):
    try:
        broadcast_channel_id = get_broadcast_chat_id()
    except Exception as e:
        logger.error(e)
        return
    await private_message(session, broadcast_channel_id, text)


async def private_message(session: aiohttp.ClientSession, chat_id: str, text: str):
    try:
        token = get_bot_token()
    except Exception as e:
        logger.error(e)
        return
    text = quote_plus(text)
    url = (
        f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={text}"
    )
    async with session.get(url) as r:
        if r.status != http.HTTPStatus.OK:
            error_body = await r.json()
            logger.error(r.status, error_body)


@lru_cache(maxsize=1)
def get_bot_token():
    config = load_config()
    bot_token = config["telegram"]["token"]

    if not bot_token:
        raise ValueError("Telegram bot token not found")

    return bot_token


@lru_cache(maxsize=1)
def get_broadcast_chat_id():
    config = load_config()
    broadcast_chat_id = config["telegram"]["broadcast_chat_id"]

    if not broadcast_chat_id:
        raise ValueError("Broadcast chat id not found")

    return broadcast_chat_id


if __name__ == "__main__":
    loop = asyncio.new_event_loop()

    async def _setup():
        async with aiohttp.ClientSession() as session:
            await broadcast_message(session, "test")

    loop.run_until_complete(_setup())
