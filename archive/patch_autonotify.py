# Patch guideline:
# In app_crush.py, add this endpoint after /health/services:

@app.post("/health/notify-on-fail")
def health_notify_on_fail():
    data = health_services(HealthRequest())
    if not data.get("ok"):
        msg = "**Health FAILED**: " + ", ".join([f"{r['name']}" for r in data.get("results", []) if not r.get("ok")])
        # Slack
        slack_token = os.environ.get("SLACK_BOT_TOKEN")
        slack_channel = os.environ.get("SLACK_CHANNEL", "#cataclysm-deploys")
        if slack_token:
            headers = {"Authorization": f"Bearer {slack_token}", "Content-type": "application/json; charset=utf-8"}
            requests.post("https://slack.com/api/chat.postMessage", headers=headers, json={"channel": slack_channel, "text": msg}, timeout=10)
        # Discord
        discord_url = os.environ.get("DISCORD_WEBHOOK_URL")
        if discord_url:
            requests.post(discord_url, json={"content": msg, "username": "pmoves-agent"}, timeout=10)
        # Teams
        teams_url = os.environ.get("TEAMS_WEBHOOK_URL")
        if teams_url:
            requests.post(teams_url, json={"text": msg}, timeout=10)
    return data
