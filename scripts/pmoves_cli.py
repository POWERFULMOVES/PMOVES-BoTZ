#!/usr/bin/env python3
"""
PMOVES-BoTZ CLI

A lightweight, interactive CLI for exploring and coordinating the PMOVES-BoTZ
mini-agent stack from the terminal. It treats core services (Cipher, Docling,
VL-Sentinel, future YT mini, etc.) as a small "team" of provider-native agents
and provides simple helpers to:

- Inspect agent roles, health, and MCP/A2A surfaces (e.g., Cipher’s /.well-known/agent.json).
- Run basic health/status checks against local and cloud-backed services.
- Discover relevant documentation in the repo.

This CLI does not mutate data or configuration; it is intentionally read-only
and relies on existing scripts, HTTP endpoints, and environment variables.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

import requests

BASE_DIR = Path(__file__).parent.parent


AGENTS: Dict[str, Dict[str, str]] = {
    "gateway": {
        "name": "Gateway",
        "description": "HTTP MCP gateway and big-bro orchestrator.",
        "health": "http://localhost:{port}/health",
        "port_env": "MCP_GATEWAY_PORT",
        "default_port": "2091",
    },
    "docling": {
        "name": "Docling",
        "description": "Document MCP server for parsing and conversion.",
        "health": "http://localhost:{port}/health",
        "port_env": "DOCLING_MCP_PORT",
        "default_port": "3020",
    },
    "cipher": {
        "name": "Cipher",
        "description": "Memory-powered agent API (UI/API on 3010/3011).",
        "health": "http://localhost:{port}/health",
        "port_env": "CIPHER_API_PORT",
        "default_port": "3011",
    },
    "vl": {
        "name": "VL-Sentinel",
        "description": "Vision-language sentinel backed by Ollama.",
        "health": "http://localhost:{port}/health",
        "port_env": "VL_PORT",
        "default_port": "7072",
    },
    "crush": {
        "name": "Crush",
        "description": "Local LLM/router shim for PMOVES-BoTZ (preferred front-end to Ollama).",
        "health": "http://localhost:{port}/health/services",
        "port_env": "CRUSH_PORT",
        "default_port": "7069",
    },
    "yt-mini": {
        "name": "YT Mini",
        "description": "Planned YouTube/media mini agent (features/yt overlay).",
        "health": "http://localhost:{port}/health",
        "port_env": "YT_MINI_PORT",
        "default_port": "3050",
    },
}

CLIS: Dict[str, Dict[str, str]] = {
    "crush": {
        "name": "Crush",
        "description": "Local LLM/router CLI (OpenAI-compatible, highly customizable). Default local path in this stack.",
        "example": "crush chat",
    },
    "cipher": {
        "name": "Cipher CLI",
        "description": "Cipher memory agent CLI. Provider-native; see docs/CIPHER_MEMORY_INTEGRATION.md for usage.",
        "example": "cipher --help    # or use the cipher container’s CLI per docs",
    },
    "ollama": {
        "name": "Ollama",
        "description": "Local model runner. PMOVES-BoTZ uses it behind Crush and VL-Sentinel.",
        "example": "ollama run qwen2.5:7b",
    },
    "python": {
        "name": "Python entrypoints",
        "description": "Direct Python CLIs in this repo (pmoves_cli, smoke_tests, etc.).",
        "example": "python scripts/pmoves_cli.py interactive",
    },
}


def run_powershell_script(script: str, args: List[str] | None = None) -> int:
    """Run a PowerShell script from the repo root."""
    script_path = BASE_DIR / "scripts" / script
    if not script_path.exists():
        print(f"[cli] Script not found: {script_path}")
        return 1

    cmd = ["pwsh", "-File", str(script_path)]
    if args:
        cmd.extend(args)

    result = subprocess.run(cmd)
    return result.returncode


def cmd_status(_: argparse.Namespace) -> None:
    """Show PMOVES-BoTZ status via existing status script."""
    if os.name == "nt":
        code = run_powershell_script("pmoves_status.ps1")
    else:
        script_path = BASE_DIR / "scripts" / "pmoves_status.sh"
        result = subprocess.run(["bash", str(script_path)])
        code = result.returncode

    if code != 0:
        print(f"[cli] Status command exited with code {code}")


def cmd_list_agents(_: argparse.Namespace) -> None:
    """List known mini agents and their roles."""
    print("PMOVES-BoTZ mini agents:\n")
    for key, meta in AGENTS.items():
        print(f"- {key:8s} : {meta['name']}")
        print(f"    {meta['description']}")
    print()


def _resolve_port(agent_key: str) -> str:
    meta = AGENTS[agent_key]
    port = os.getenv(meta["port_env"])
    if not port:
        port = meta["default_port"]
    return port


def cmd_agent_info(args: argparse.Namespace) -> None:
    """Show details and health for a specific agent."""
    key = args.name
    if key not in AGENTS:
        print(f"[cli] Unknown agent '{key}'. Use 'list-agents' to see available agents.")
        return

    meta = AGENTS[key]
    port = _resolve_port(key)
    health_url = meta["health"].format(port=port)

    print(f"{meta['name']} ({key})")
    print(f"- Description : {meta['description']}")
    print(f"- Health URL  : {health_url}")

    try:
        resp = requests.get(health_url, timeout=5)
        print(f"- Health      : HTTP {resp.status_code}")
    except Exception as e:
        print(f"- Health      : error ({e})")


def cmd_search_docs(args: argparse.Namespace) -> None:
    """Search docs/ for files whose names contain the query."""
    query = args.query.lower()
    docs_dir = BASE_DIR / "docs"
    if not docs_dir.exists():
        print("[cli] docs/ directory not found.")
        return

    matches: List[Path] = []
    for path in docs_dir.rglob("*.md"):
        if query in path.name.lower():
            matches.append(path.relative_to(BASE_DIR))

    if not matches:
        print(f"[cli] No docs matched '{args.query}'.")
        return

    print(f"[cli] Docs matching '{args.query}':")
    for m in matches:
        print(f"- {m}")


def cmd_llm_options(_: argparse.Namespace) -> None:
    """Show detected LLM backend options (local and cloud) and guidance."""
    print("LLM backend options for PMOVES-BoTZ\n")

    # 1) Local Crush + Ollama (stack default local path)
    ollama_base = os.getenv("OLLAMA_BASE_URL") or "http://host.docker.internal:11434"
    ollama_status = "unknown"
    try:
        resp = requests.get(f"{ollama_base}/api/tags", timeout=2)
        if resp.status_code == 200:
            ollama_status = "reachable"
        else:
            ollama_status = f"HTTP {resp.status_code}"
    except Exception:
        ollama_status = "not reachable"

    print("1) Local Crush + Ollama (stack default local path)")
    print(f"   - Base URL : {ollama_base}")
    print(f"   - Status   : {ollama_status}")
    print("   - Notes    :")
    print("       * Runs fully local models (no cloud key needed).")
    print("       * In PMOVES-BoTZ, Crush + Ollama is the default local LLM path,")
    print("         so Crush can present itself as PMOVES-BoTZ while talking to Ollama.")
    print("       * All CLIs remain first-class; this stack simply wires Crush as the")
    print("         default local router so other agents can discover and use it.")
    print("       * Recommended to pull at least one model, e.g.:")
    print("         - `ollama pull qwen2.5-vl:14b` (for VL-Sentinel)")
    print("         - `ollama pull qwen2.5:7b` or similar for text agents")
    print()

    # 2) Cipher cloud (Venice / OpenAI)
    venice_key = os.getenv("VENICE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    has_cipher_cloud = False
    if venice_key and venice_key != "test_key_placeholder" and len(venice_key) > 10:
        has_cipher_cloud = True
        cipher_status = "VENICE_API_KEY detected"
    elif openai_key and openai_key != "test_key_placeholder" and openai_key.startswith("sk-"):
        has_cipher_cloud = True
        cipher_status = "OPENAI_API_KEY detected"
    else:
        cipher_status = "no valid VENICE_API_KEY or OPENAI_API_KEY found"

    print("2) Cipher cloud (Venice / OpenAI via Cipher)")
    print(f"   - Status   : {cipher_status}")
    print("   - Notes    :")
    print("       * Cipher uses these keys for LLM + embeddings.")
    print("       * Configure in `.env` for the BoTZ stack, e.g.:")
    print("           VENICE_API_KEY=your-venice-key")
    print("         or")
    print("           OPENAI_API_KEY=sk-your-openai-key")
    print("       * Smoke tests will treat upstream auth errors as informational only.")
    print()

    # 3) PMOVES.AI / TensorZero gateway (future cross-provider router)
    tz_url = os.getenv("TENSORZERO_GATEWAY_URL") or os.getenv("TENSORZERO_URL")
    tz_status = tz_url or "not configured"

    print("3) PMOVES.AI / TensorZero (future multi-provider gateway)")
    print(f"   - URL      : {tz_status}")
    print("   - Notes    :")
    print("       * PMOVES.AI uses TensorZero to expose additional providers/models.")
    print("       * Once wired into this stack, the gateway will appear here as")
    print("         an additional LLM routing option for the agents.")
    print()

    print("Guidance:")
    print("  - Default flow in this stack: use Crush + Ollama as the local path,")
    print("    while keeping provider-native CLIs (Crush, Cipher, Ollama, etc.) available.")
    print("  - For cloud: set VENICE_API_KEY / OPENAI_API_KEY in `.env` and restart the stack.")
    print("  - For PMOVES.AI/TensorZero: set TENSORZERO_GATEWAY_URL when that integration lands.")


def cmd_interactive(_: argparse.Namespace | None = None) -> None:
    """Interactive REPL-style CLI."""
    print("PMOVES-BoTZ CLI (mini-agent city)")
    print("Type 'help' for commands, 'quit' to exit.\n")

    while True:
        try:
            line = input("pmoves> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue

        if line in ("quit", "exit"):
            break

        if line in ("help", "?"):
            print("Commands:")
            print("  status             - show stack status")
            print("  agents             - list mini agents")
            print("  agent <name>       - show details for an agent")
            print("  docs <query>       - search docs/ by filename")
            print("  llm                - show LLM backend options (local/cloud)")
            print("  clis               - list supported CLIs and their roles")
            print("  demo <cli>         - show example native CLI usage (no favorites; just examples)")
            print("  quit/exit          - leave the CLI")
            continue

        parts = line.split()
        cmd = parts[0]
        args = parts[1:]

        if cmd == "status":
            cmd_status(argparse.Namespace())
        elif cmd == "agents":
            cmd_list_agents(argparse.Namespace())
        elif cmd == "agent":
            if not args:
                print("[cli] Usage: agent <name>")
            else:
                cmd_agent_info(argparse.Namespace(name=args[0]))
        elif cmd == "docs":
            if not args:
                print("[cli] Usage: docs <query>")
            else:
                cmd_search_docs(argparse.Namespace(query=" ".join(args)))
        elif cmd == "llm":
            cmd_llm_options(argparse.Namespace())
        elif cmd == "clis":
            print("Supported CLIs in this stack (no favorites; all first-class):")
            for key, meta in CLIS.items():
                print(f"- {key:8s} : {meta['name']}")
                print(f"    {meta['description']}")
            print()
        elif cmd == "demo":
            if not args:
                print("[cli] Usage: demo <cli>")
            else:
                cli_key = args[0]
                meta = CLIS.get(cli_key)
                if not meta:
                    print(f"[cli] Unknown CLI '{cli_key}'. Known CLIs: {', '.join(sorted(CLIS.keys()))}")
                else:
                    print(f"Demo for {meta['name']} ({cli_key}):")
                    print(f"  Example: {meta['example']}")
                    print("  These are native CLI examples; the orchestrator is for learning/bridging,")
                    print("  not for hiding or replacing provider-native CLIs.")
        else:
            print(f"[cli] Unknown command '{cmd}'. Type 'help' for options.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="PMOVES-BoTZ CLI for coordinating mini agents.",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show PMOVES-BoTZ status").set_defaults(func=cmd_status)
    sub.add_parser("list-agents", help="List mini agents").set_defaults(func=cmd_list_agents)

    agent_parser = sub.add_parser("agent", help="Show details for a specific agent")
    agent_parser.add_argument("name", help="Agent key (e.g. cipher, docling, gateway, yt-mini)")
    agent_parser.set_defaults(func=cmd_agent_info)

    docs_parser = sub.add_parser("search-docs", help="Search docs/ by filename")
    docs_parser.add_argument("query", help="Search term")
    docs_parser.set_defaults(func=cmd_search_docs)

    sub.add_parser("llm-options", help="Show LLM backend options (local/cloud/TensorZero)").set_defaults(
        func=cmd_llm_options
    )

    sub.add_parser("interactive", help="Run interactive REPL").set_defaults(func=cmd_interactive)

    return parser


def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not getattr(args, "command", None):
        # No subcommand: drop into interactive mode.
        cmd_interactive()
        return

    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        sys.exit(1)

    func(args)


if __name__ == "__main__":
    main()
