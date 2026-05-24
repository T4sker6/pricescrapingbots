#!/bin/bash
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99

# Powiadomienia raz dziennie o 16:00 czasu warszawskiego (UTC+2)
(crontab -l 2>/dev/null; echo "0 14 * * * python3 /app/notify_discord.py >> /app/notify.log 2>&1") | crontab -

cron

python3 /app/api.py &

python3 /app/discord_bot.py
