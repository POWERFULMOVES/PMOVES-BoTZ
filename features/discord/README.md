# Discord Bot (pmoves-mini)
Slash commands:
- `/health` → calls SHIM_BASE `/health/services`
- `/notify` → posts via shim to Discord/Slack

Run:
```bash
export DISCORD_BOT_TOKEN=... 
export SHIM_BASE=https://<tailscale-or-ingress>
docker build -t pmoves-discord-bot ./discord_bot
docker run --rm -e DISCORD_BOT_TOKEN -e SHIM_BASE pmoves-discord-bot
```