"""
PMOVES Discord Bot - MCP-enabled agent interface.

Features:
- Health monitoring for PMOVES services
- MCP tool execution via gateway
- TTS synthesis with voice personas
- Agent query and conversation

Reference: docs/agents/AI Agent Integration and Best Practices.md
"""

import os
import asyncio
import json
import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
import httpx

# Configuration
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
GUILD_ID = os.environ.get("DISCORD_GUILD_ID")
SHIM_BASE = os.environ.get("SHIM_BASE", "http://localhost:7069")
GATEWAY_BASE = os.environ.get("GATEWAY_BASE", "http://localhost:7070")
TTS_BASE = os.environ.get("TTS_BASE", "http://localhost:8090")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


# HTTP client for API calls
http_client: Optional[httpx.AsyncClient] = None


async def get_http_client() -> httpx.AsyncClient:
    """Get or create HTTP client."""
    global http_client
    if http_client is None:
        http_client = httpx.AsyncClient(timeout=60.0)
    return http_client


@bot.event
async def on_ready():
    """Bot startup handler."""
    logger.info(f"Bot ready as {bot.user}")
    try:
        if GUILD_ID:
            await bot.tree.sync(guild=discord.Object(id=int(GUILD_ID)))
        else:
            await bot.tree.sync()
        logger.info("Slash commands synced")
    except Exception as e:
        logger.error(f"Sync failed: {e}")


@bot.event
async def on_close():
    """Bot shutdown handler."""
    global http_client
    if http_client:
        await http_client.aclose()


# =============================================================================
# Health Commands
# =============================================================================

@bot.tree.command(name="health", description="Check PMOVES service health")
async def health_cmd(interaction: discord.Interaction):
    """Probe PMOVES services health."""
    await interaction.response.defer(thinking=True)

    client = await get_http_client()
    try:
        r = await client.post(f"{SHIM_BASE}/health/services", json={})
        data = r.json()
        status = "OK" if data.get("ok") else "FAIL"
        lines = [f"**Health {status}**"]
        for item in data.get("results", []):
            icon = "+" if item.get("ok") else "-"
            status_text = item.get("status", "?")
            if not item.get("ok"):
                status_text = f"FAIL ({item.get('error') or status_text})"
            lines.append(f"{icon} {item['name']}: {status_text}")
        await interaction.followup.send("```diff\n" + "\n".join(lines) + "\n```")
    except Exception as e:
        await interaction.followup.send(f"Health check failed: {e}")


@bot.tree.command(name="gateway", description="Check MCP Gateway status")
async def gateway_cmd(interaction: discord.Interaction):
    """Check MCP Gateway and list available tools."""
    await interaction.response.defer(thinking=True)

    client = await get_http_client()
    try:
        r = await client.get(f"{GATEWAY_BASE}/health")
        health = r.json()

        r2 = await client.get(f"{GATEWAY_BASE}/tools")
        tools = r2.json()

        lines = [
            f"**MCP Gateway** - {health.get('status', 'unknown')}",
            f"Servers: {health.get('servers', 0)}",
            f"Tools: {len(tools.get('tools', []))}",
            "",
            "**Available Tools:**",
        ]
        for tool in tools.get("tools", [])[:15]:  # Limit to 15
            lines.append(f"- `{tool['name']}`")
        if len(tools.get("tools", [])) > 15:
            lines.append(f"... and {len(tools['tools']) - 15} more")

        await interaction.followup.send("\n".join(lines))
    except Exception as e:
        await interaction.followup.send(f"Gateway check failed: {e}")


# =============================================================================
# MCP Tool Execution
# =============================================================================

@bot.tree.command(name="tool", description="Execute an MCP tool")
@app_commands.describe(
    tool_name="Name of the MCP tool to execute",
    arguments="JSON arguments for the tool (optional)",
)
async def tool_cmd(
    interaction: discord.Interaction,
    tool_name: str,
    arguments: str = "{}",
):
    """Execute an MCP tool via the gateway."""
    await interaction.response.defer(thinking=True)

    # Parse arguments
    try:
        args = json.loads(arguments) if arguments else {}
    except json.JSONDecodeError as e:
        await interaction.followup.send(f"Invalid JSON arguments: {e}")
        return

    client = await get_http_client()
    try:
        r = await client.post(
            f"{GATEWAY_BASE}/tools/{tool_name}",
            json={"arguments": args},
        )
        result = r.json()

        if "error" in result:
            await interaction.followup.send(f"Tool error: {result['error']}")
        else:
            # Format result
            content = result.get("result", result)
            if isinstance(content, dict):
                content = json.dumps(content, indent=2)
            if len(str(content)) > 1900:
                content = str(content)[:1900] + "..."
            await interaction.followup.send(f"**{tool_name}** result:\n```json\n{content}\n```")

    except Exception as e:
        await interaction.followup.send(f"Tool execution failed: {e}")


@bot.tree.command(name="tools", description="List available MCP tools")
@app_commands.describe(search="Search filter for tool names (optional)")
async def tools_cmd(interaction: discord.Interaction, search: str = ""):
    """List available MCP tools."""
    await interaction.response.defer(thinking=True)

    client = await get_http_client()
    try:
        r = await client.get(f"{GATEWAY_BASE}/tools")
        data = r.json()
        tools = data.get("tools", [])

        if search:
            tools = [t for t in tools if search.lower() in t["name"].lower()]

        if not tools:
            await interaction.followup.send("No tools found.")
            return

        lines = [f"**MCP Tools** ({len(tools)} found):"]
        for tool in tools[:20]:
            desc = tool.get("description", "")[:50]
            lines.append(f"- `{tool['name']}`: {desc}")
        if len(tools) > 20:
            lines.append(f"... and {len(tools) - 20} more")

        await interaction.followup.send("\n".join(lines))

    except Exception as e:
        await interaction.followup.send(f"Failed to list tools: {e}")


# =============================================================================
# TTS Commands
# =============================================================================

@bot.tree.command(name="speak", description="Generate speech from text")
@app_commands.describe(
    text="Text to synthesize",
    persona="Voice persona (host, architect, ops)",
)
@app_commands.choices(persona=[
    app_commands.Choice(name="Host (warm, natural)", value="host"),
    app_commands.Choice(name="Architect (fast, excited)", value="architect"),
    app_commands.Choice(name="Ops (gritty, authoritative)", value="ops"),
])
async def speak_cmd(
    interaction: discord.Interaction,
    text: str,
    persona: str = "host",
):
    """Generate speech from text using TTS."""
    await interaction.response.defer(thinking=True)

    if len(text) > 1000:
        await interaction.followup.send("Text too long (max 1000 characters)")
        return

    client = await get_http_client()
    try:
        r = await client.post(
            f"{TTS_BASE}/synthesize",
            json={
                "text": text,
                "persona": persona,
                "format": "mp3",
            },
            timeout=120.0,
        )
        result = r.json()

        if result.get("error"):
            await interaction.followup.send(f"TTS error: {result['error']}")
        elif result.get("audio_url"):
            await interaction.followup.send(
                f"**{persona.title()} Voice**\n{result['audio_url']}"
            )
        else:
            await interaction.followup.send("TTS completed but no audio URL returned")

    except Exception as e:
        await interaction.followup.send(f"TTS failed: {e}")


# =============================================================================
# Agent Commands
# =============================================================================

@bot.tree.command(name="ask", description="Ask the PMOVES agent a question")
@app_commands.describe(question="Your question for the agent")
async def ask_cmd(interaction: discord.Interaction, question: str):
    """Ask the PMOVES agent a question."""
    await interaction.response.defer(thinking=True)

    client = await get_http_client()
    try:
        # Try to use the agent endpoint if available
        r = await client.post(
            f"{GATEWAY_BASE}/agent/query",
            json={"query": question, "context": "discord"},
            timeout=120.0,
        )
        result = r.json()

        response = result.get("response", result.get("result", str(result)))
        if len(response) > 1900:
            response = response[:1900] + "..."

        await interaction.followup.send(f"**Agent Response:**\n{response}")

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            await interaction.followup.send("Agent endpoint not available. Use `/tool` to execute specific tools.")
        else:
            await interaction.followup.send(f"Agent query failed: {e}")
    except Exception as e:
        await interaction.followup.send(f"Agent query failed: {e}")


# =============================================================================
# Notification Commands
# =============================================================================

@bot.tree.command(name="notify", description="Send a notification via shim")
@app_commands.describe(
    text="Message text",
    channel="Slack channel (optional)",
)
async def notify_cmd(
    interaction: discord.Interaction,
    text: str,
    channel: Optional[str] = None,
):
    """Send a notification via the shim to Discord and Slack."""
    await interaction.response.defer(thinking=True)

    client = await get_http_client()
    try:
        await client.post(f"{SHIM_BASE}/notify/discord", json={"content": text})
        await client.post(
            f"{SHIM_BASE}/notify/slack",
            json={"text": text, "channel": channel},
        )
        await interaction.followup.send("Notification sent.")
    except Exception as e:
        await interaction.followup.send(f"Notification failed: {e}")


# =============================================================================
# A2A Commands
# =============================================================================

@bot.tree.command(name="agents", description="List available A2A agents")
async def agents_cmd(interaction: discord.Interaction):
    """List agents available via A2A protocol."""
    await interaction.response.defer(thinking=True)

    client = await get_http_client()
    try:
        r = await client.get(f"{GATEWAY_BASE}/.well-known/agent.json")
        card = r.json()

        lines = [
            f"**{card.get('name', 'Agent')}**",
            f"Version: {card.get('version', 'unknown')}",
            "",
            "**Capabilities:**",
        ]
        for cap in card.get("capabilities", []):
            lines.append(f"- {cap}")

        lines.append("")
        lines.append("**Skills:**")
        for skill in card.get("skills", [])[:10]:
            lines.append(f"- `{skill.get('id')}`: {skill.get('name', '')}")

        await interaction.followup.send("\n".join(lines))

    except Exception as e:
        await interaction.followup.send(f"Failed to fetch agent card: {e}")


@bot.tree.command(name="task", description="Create an A2A task")
@app_commands.describe(
    skill="Skill ID to execute",
    message="Message/input for the task",
)
async def task_cmd(
    interaction: discord.Interaction,
    skill: str,
    message: str,
):
    """Create and execute an A2A task."""
    await interaction.response.defer(thinking=True)

    client = await get_http_client()
    try:
        r = await client.post(
            f"{GATEWAY_BASE}/a2a",
            json={
                "jsonrpc": "2.0",
                "method": "tasks/create",
                "params": {
                    "skill_id": skill,
                    "message": message,
                    "auto_execute": True,
                },
                "id": 1,
            },
            timeout=120.0,
        )
        result = r.json()

        if "error" in result:
            await interaction.followup.send(f"Task error: {result['error']}")
        else:
            task = result.get("result", {})
            state = task.get("state", "unknown")
            task_id = task.get("id", "")[:8]

            lines = [
                f"**Task Created** (`{task_id}`)",
                f"State: {state}",
                f"Skill: {skill}",
            ]

            # If completed, show result
            artifacts = task.get("artifacts", [])
            if artifacts:
                lines.append("")
                lines.append("**Result:**")
                for art in artifacts[:3]:
                    content = str(art.get("data", ""))[:500]
                    lines.append(f"```\n{content}\n```")

            await interaction.followup.send("\n".join(lines))

    except Exception as e:
        await interaction.followup.send(f"Task creation failed: {e}")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("Set DISCORD_BOT_TOKEN environment variable")
    bot.run(TOKEN)
