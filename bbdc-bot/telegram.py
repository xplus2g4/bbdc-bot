import asyncio
from urllib.parse import quote_plus

import aiohttp

from .config import load_config


async def send_message(session: aiohttp.ClientSession, text: str):
    try:
        token, chat_id = get_token_chat_id()
    except Exception as e:
        print(e)
        return
    text = quote_plus(text)
    url = (
        f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={text}"
    )
    async with session.get(url) as r:
        pass


def get_token_chat_id():
    config = load_config()
    enabled = config["telegram"]["enabled"]
    if not enabled:
        raise ValueError("Telegram bot not enabled")
    bot_token = config["telegram"]["token"]
    chat_id = config["telegram"]["chat_id"]

    if not bot_token:
        raise ValueError("Telegram bot token not found")
    if not chat_id:
        raise ValueError("Telegram chat_id not found")

    return (bot_token, chat_id)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()

    async def _setup():
        async with aiohttp.ClientSession() as session:
            await send_message(session, "bye")

    loop.run_until_complete(_setup())
