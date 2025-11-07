# Slack + Discord setup

## Slack
1) Create app from manifest → use `slack_app_manifest.yaml`.
2) Install → copy Bot token → set `SLACK_BOT_TOKEN` in `.env`.
3) Optional: point `/deploy` and `/health` slash commands at your n8n or shim URLs.

## Discord
1) Create a bot, get token.
2) Build & run `./discord_bot` with `DISCORD_BOT_TOKEN` + `SHIM_BASE`.
3) Use `/health` and `/notify` inside your server.