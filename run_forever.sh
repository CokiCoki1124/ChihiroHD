#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

if [ -z "${DISCORD_TOKEN:-}" ]; then
  echo "ERROR: DISCORD_TOKEN is not set."
  echo "Set it with: export DISCORD_TOKEN=\"your-token-here\""
  exit 1
fi

LOG_FILE="$(pwd)/bot.log"
PID_FILE="$(pwd)/.bot.pid"

if [ "${1:-}" != "background" ]; then
  echo "Starting ChihiroHD bot in detached mode..."
  nohup bash "$0" background >> "$LOG_FILE" 2>&1 &
  DETACHED_PID=$!
  echo "$DETACHED_PID" > "$PID_FILE"
  echo "Detached PID: $DETACHED_PID"
  echo "Logs: $LOG_FILE"
  exit 0
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Starting bot" >> "$LOG_FILE"

while true; do
  echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Launching bot process" >> "$LOG_FILE"
  python3 bot.py >> "$LOG_FILE" 2>&1
  EXIT_CODE=$?
  if [ "$EXIT_CODE" -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Bot exited normally. Stopping restart loop." >> "$LOG_FILE"
    break
  fi
  echo "$(date '+%Y-%m-%d %H:%M:%S') [WARN] Bot stopped with exit code $EXIT_CODE. Restarting in 5 seconds..." >> "$LOG_FILE"
  sleep 5
  echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Restarting bot" >> "$LOG_FILE"
  sleep 1
done
