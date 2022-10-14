# BBDC-bot

BBDC Practical Slot Booking Bot

>Note: TPDS booking not included

## Functionality
- Periodically check and book practical lessons
- Send Telegram message when booking is confirmed

## Getting Started

### Requirements
- `Docker Desktop ^4.11.1`
- `docker-compose ^2.7.0`

### Running the script

1. Setup a Telegram bot via [@BotFather](https://t.me/botfather)
2. Get your chat id via [@RawDataBot](https://t.me/RawDataBot), it should look something like this: `512345678`
3. Create your own config under the `config` folder using the template: [config/example.yaml](config/example.yaml)
4. Update `CONFIG_PATH` env in [docker-compose.yml](docker-compose.yml)
5. In your terminal run: `docker compose up -d`

## Booking Configs

All configs are compulsory

| Config | Description |
| ------ | ----------- |
| `interval` | Query interval, in minutes |
| `bbdc.username` | BBDC Username |
| `bbdc.password` | BBDC Password |
| `booking.want_sessions` | Preferred sessions |
| `booking.want_months` | Preferred months, in Mmm/YYYY (e.g. Oct/2022) |
| `booking.want_dates` | Specific dates, in YYYY-MM-DD (e.g. 2022-10-31) |
| `telegram.token` | Telegram bot token |
| `telegram.chat_id` | Telegram chat id |
