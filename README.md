# BBDC-bot

BBDC Practical Slot Booking Bot

>Note: TPDS booking not included

>Note2: Adapted to the new BBDC UI, slot finding implemented, auto-booking W.I.P.

## Functionality
- Periodically check and book practical lessons
- Send Telegram message when booking is confirmed

## Getting Started

### Requirements
- `Docker Desktop ^4.11.1`
- `docker-compose ^2.7.0`

### Running the script

## Setup
1. Setup a Telegram bot via [@BotFather](https://t.me/botfather)
2. Get your chat id via [@RawDataBot](https://t.me/RawDataBot), it should look something like this: `512345678`
3. Create your own config under the `config` folder using the template: [config/example.yaml](config/example.yaml)

## Docker
1. Update `CONFIG_PATH` env in [docker-compose.yml](docker-compose.yml)
2. In your terminal run: `docker compose up -d`

## Local
1. `export CONFIG_PATH=config/my_config.yaml`
2. `poetry shell`
3. `poetry install`
4. `poetry run bbdc-bot`

## Booking Configs

All configs are compulsory

| Config | Description |
| ------ | ----------- |
| `interval` | Query interval, in minutes |
| `accounts.username` | BBDC Username |
| `accounts.password` | BBDC Password |
| `booking.want_sessions` | Preferred sessions |
| `booking.want_months` | Preferred months, in YYYYMM (e.g. 202211) |
| `telegram.enabled` | Enables Telegram bot (true/fales) |
| `telegram.token` | Telegram bot token |
| `telegram.chat_id` | Telegram chat id |
