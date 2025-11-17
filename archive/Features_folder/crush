import os, subprocess, time, requests
from typing import Optional, List, Dict
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="pmoves portable shim")

class CrushRequest(BaseModel):
    command: str = "crush"
    args: Optional[List[str]] = None
    spec: str = "pmoves==latest"
    timeout: int = 900

@app.post("/crush")
def run_crush(req: CrushRequest):
    args = req.args or []
    cmd = ["python3","-m","pipx","run","--spec",req.spec,"python","-m","pmoves.tools.mini_cli", req.command, *args]
    out = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=req.timeout, text=True, env=os.environ.copy())
    return {"ok": out.returncode == 0, "code": out.returncode, "output": out.stdout[-8000:]}

class DiscordPayload(BaseModel):
    webhook_url: Optional[str] = None
    content: str
    username: Optional[str] = "pmoves-agent"
    embeds: Optional[List[Dict]] = None

@app.post("/notify/discord")
def notify_discord(body: DiscordPayload):
    url = body.webhook_url or os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        return {"ok": False, "error": "Missing webhook_url and DISCORD_WEBHOOK_URL"}
    payload = {"content": body.content}
    if body.username: payload["username"] = body.username
    if body.embeds: payload["embeds"] = body.embeds
    r = requests.post(url, json=payload, timeout=15)
    return {"ok": r.ok, "status": r.status_code, "text": r.text[-2000:]}

class SlackPayload(BaseModel):
    bot_token: Optional[str] = None
    channel: Optional[str] = None
    text: str
    blocks: Optional[List[Dict]] = None

@app.post("/notify/slack")
def notify_slack(body: SlackPayload):
    token = body.bot_token or os.environ.get("SLACK_BOT_TOKEN")
    channel = body.channel or os.environ.get("SLACK_CHANNEL", "#cataclysm-deploys")
    if not token or not channel:
        return {"ok": False, "error": "Missing bot_token or channel"}
    headers = {"Authorization": f"Bearer {token}", "Content-type": "application/json; charset=utf-8"}
    payload = {"channel": channel, "text": body.text}
    if body.blocks: payload["blocks"] = body.blocks
    r = requests.post("https://slack.com/api/chat.postMessage", headers=headers, json=payload, timeout=15)
    try:
        data = r.json()
    except Exception:
        data = {"raw": r.text[-2000:]}
    return {"ok": bool(data.get("ok")) if isinstance(data, dict) else r.ok, "status": r.status_code, "data": data}

class TeamsPayload(BaseModel):
    webhook_url: Optional[str] = None
    text: str

@app.post("/notify/teams")
def notify_teams(body: TeamsPayload):
    url = body.webhook_url or os.environ.get("TEAMS_WEBHOOK_URL")
    if not url:
        return {"ok": False, "error": "Missing webhook_url and TEAMS_WEBHOOK_URL"}
    payload = {"text": body.text}
    r = requests.post(url, json=payload, timeout=15)
    return {"ok": r.ok, "status": r.status_code, "text": r.text[-2000:]}

class HealthTarget(BaseModel):
    name: str
    url: str
    expect_status: int = 200

class HealthRequest(BaseModel):
    targets: Optional[List[HealthTarget]] = None
    timeout: int = 8

@app.post("/health/services")
def health_services(body: HealthRequest):
    if not body.targets:
        env = os.environ
        defaults = []
        if env.get("HIRAG_URL"): defaults.append({"name":"hirag","url":env["HIRAG_URL"]})
        if env.get("MEILI_URL"): defaults.append({"name":"meili","url":env["MEILI_URL"]})
        if env.get("QDRANT_URL"): defaults.append({"name":"qdrant","url":env["QDRANT_URL"]})
        if env.get("NEO4J_URL"): defaults.append({"name":"neo4j","url":env["NEO4J_URL"]})
        if env.get("MINIO_ENDPOINT"):
            proto = "https" if env.get("MINIO_SECURE","false").lower() in ("1","true","yes") else "http"
            defaults.append({"name":"minio","url": f"{proto}://{env['MINIO_ENDPOINT']}"})
        body.targets = [HealthTarget(**t) for t in defaults]
    results = []
    for t in body.targets:
        try:
            r = requests.get(t.url, timeout=body.timeout)
            ok = (r.status_code == t.expect_status)
            results.append({"name": t.name, "url": t.url, "status": r.status_code, "ok": ok})
        except Exception as e:
            results.append({"name": t.name, "url": t.url, "error": str(e), "ok": False})
    overall = all(x.get("ok") for x in results) if results else False
    return {"ok": overall, "results": results, "ts": int(time.time())}

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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7069)