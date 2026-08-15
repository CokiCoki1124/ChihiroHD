#!/bin/bash

# Run this script from the workspace root: ./run.sh
# Make sure you have a valid Discord bot token first.

if [ -z "$DISCORD_TOKEN" ]; then
  echo "ERROR: DISCORD_TOKEN is not set."
  echo "Set it with: export DISCORD_TOKEN=\"your-token-here\""
  exit 1
fi

cd "$(dirname "$0")"
nohup python3 bot.py > bot.log 2>&1 &
PID=$!
echo "Bot started with PID $PID"
echo "Logs: $(pwd)/bot.log"
