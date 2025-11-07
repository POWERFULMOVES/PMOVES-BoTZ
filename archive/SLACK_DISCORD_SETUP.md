# Slack + Discord setup (pmoves-mini)

## Slack
1) Create app from manifest → use `slack_app_manifest.yaml`.
2) Install → copy Bot token → set `SLACK_BOT_TOKEN` in your `.env`.
3) Optional: wire slash commands `/deploy` and `/health` to n8n or the shim.

## Discord
1) Create bot → copy token → set `DISCORD_BOT_TOKEN`.
2) Build & run:
   ```bash
   docker build -t pmoves-discord-bot ./discord_bot
   docker run --rm -e DISCORD_BOT_TOKEN -e SHIM_BASE=https://<tailscale-or-ingress> pmoves-discord-bot
   ```

## Health auto-notify
Call `POST /health/notify-on-fail` on the shim to probe services and post failures to your branded channels.
