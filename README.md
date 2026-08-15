# ChihiroHD

## Bot startup

This repository includes two startup scripts:

- `run.sh` — launch the bot once in the background.
- `run_forever.sh` — launch the bot in detached mode and restart automatically if it stops, which is suitable for 24/7 operation.

### Run once

```bash
export DISCORD_TOKEN="YOUR_BOT_TOKEN"
./run.sh
```

### Run with auto-restart

```bash
export DISCORD_TOKEN="YOUR_BOT_TOKEN"
./run_forever.sh
```

### Check status

```bash
ps -ef | grep '[p]ython3 bot.py'
tail -n 20 bot.log
```
