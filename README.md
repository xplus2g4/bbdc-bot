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

1. Setup a Telegram bot via [@botfather](https://t.me/botfather)
2. Get your chat id via [@RawDataBot](https://t.me/RawDataBot), it should look something like this: `512345678`
3. Setup config using the template: [config/example.yaml](config/example.yaml)
4. Update `CONFIG_PATH` env in [docker-compose.yml](docker-compose.yml)
5. In your terminal run: `docker compose up -d`