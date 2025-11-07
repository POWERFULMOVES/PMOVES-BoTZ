import os, asyncio, httpx
import discord
from discord import app_commands
from discord.ext import commands

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
GUILD_ID = os.environ.get("DISCORD_GUILD_ID")
SHIM_BASE = os.environ.get("SHIM_BASE","http://localhost:7069")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    try:
        if GUILD_ID:
            await bot.tree.sync(guild=discord.Object(id=int(GUILD_ID)))
        else:
            await bot.tree.sync()
        print("Slash commands synced")
    except Exception as e:
        print("Sync failed:", e)

@bot.tree.command(name="health", description="Probe pmoves services")
async def health_cmd(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(f"{SHIM_BASE}/health/services", json={})
    data = r.json()
    status = "✅ OK" if data.get("ok") else "❌ FAIL"
    lines = [f"**Health {status}**"]
    for item in data.get("results", []):
        if item.get("ok"):
            lines.append(f"- {item['name']}: {item.get('status','?')}")
        else:
            lines.append(f"- {item['name']}: FAIL ({item.get('error') or item.get('status')})")
    await interaction.followup.send("\n".join(lines))

@bot.tree.command(name="notify", description="Send a message via the shim")
@app_commands.describe(text="message text", channel="Slack channel (optional)")
async def notify_cmd(interaction: discord.Interaction, text: str, channel: str | None = None):
    await interaction.response.defer(thinking=True)
    async with httpx.AsyncClient(timeout=15) as client:
        await client.post(f"{SHIM_BASE}/notify/discord", json={"content": text})
        await client.post(f"{SHIM_BASE}/notify/slack", json={"text": text, "channel": channel})
    await interaction.followup.send("Notified via shim.")

if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("Set DISCORD_BOT_TOKEN")
    bot.run(TOKEN)