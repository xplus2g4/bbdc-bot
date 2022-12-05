# BBDC-bot

BBDC Practical Slot Booking Bot

>Note: TPDS booking not included

>Note2: Supports the new BBDC UI

## Features
- Periodically check and book practical lessons
- Send Telegram message when booking is found
- Auto book preferred slots

## Getting Started

## Pre-requisites
1. Setup a Telegram bot via [@BotFather](https://t.me/botfather)
2. Get your chat id via [@RawDataBot](https://t.me/RawDataBot), it should look something like this: `512345678`
3. Create your own config under the `config` folder using the template: [config/example.yaml](config/example.yaml)

## Docker
### Requirements
- `Docker Desktop ^4.11.1`
- `docker-compose ^2.7.0`
### Deployment
1. Update `CONFIG_PATH` env in [docker-compose.yml](docker-compose.yml)
2. In your console run: `docker compose up -d`

## Local
### Requirements
- `Poetry ^1.1.13`
### Deployment
1. `export CONFIG_PATH=config/my_config.yaml`
2. `poetry shell`
3. `poetry install`
4. `python -m bbdc-bot`

## Booking Configs

| Config | Description |
| ------ | ----------- |
| `interval` | Query interval, in minutes, preferably 50 minutes to prevent getting blacklisted |
| `course_type` | Course Type for which you want to book slots |
| `query_months` | Preferred months, in YYYYMM (e.g. 202211) |
||
| `accounts` |
| `.username` | BBDC Username (Supports multiple account) |
| `.password` | BBDC Password |
| `.chat_id` | Telegram chat id, telegram bot will send a message to this chat when a slot is booked |
| `.preferred_slots` |
| `.date` | Preferred date in YYYY-MM-DD |
| `.sessions` | Preferred sessions |
||
| `telegram.token` | Telegram bot token |
| `telegram.broadcast_chat_id` | Telegram chat to broadcast the found slots. Can be personal chat or a channel |

## FAQ
> How do I know if my config is loaded properly?

Test it with `python -m bbdc-bot.config`. You should see your configs printed in your console.

> How do I know if my telegram bot is working?

Test it with `python -m bbdc-bot.telegram`. You should see the message "test" being sent to your chat.
