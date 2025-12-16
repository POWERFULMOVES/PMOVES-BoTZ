#!/usr/bin/env python3
"""
Register all BoTZ tool metadata to cipher memory.

This script stores documentation about each MCP tool in cipher memory,
enabling cross-agent awareness and intelligent tool suggestions.

Usage:
    python scripts/register_tools_to_cipher.py
"""

import json
import os
import subprocess
from typing import Any, Dict, List

# Tool definitions with metadata
BOTZ_TOOLS: List[Dict[str, Any]] = [
    # n8n-agent tools
    {
        "name": "n8n-agent",
        "description": "n8n Workflow Automation Agent - Manages and executes n8n workflows",
        "category": "automation",
        "tools": [
            {"name": "n8n_list_workflows", "description": "List all n8n workflows with status"},
            {"name": "n8n_get_workflow", "description": "Get workflow details by ID"},
            {"name": "n8n_execute_workflow", "description": "Execute workflow with input data"},
            {"name": "n8n_create_workflow", "description": "Create new workflow from JSON"},
            {"name": "n8n_update_workflow", "description": "Update existing workflow"},
            {"name": "n8n_toggle_workflow", "description": "Activate/deactivate workflow"},
            {"name": "n8n_search_skills", "description": "Search for automation patterns"},
            {"name": "n8n_suggest_workflow", "description": "Get AI workflow suggestions"},
        ],
        "use_when": [
            "Automating recurring tasks",
            "Building workflow pipelines",
            "Connecting external services",
            "Scheduling automated jobs",
        ],
    },
    # Hostinger tools
    {
        "name": "hostinger",
        "description": "Hostinger VPS/DNS/Domain Management - Manage hosting infrastructure",
        "category": "infrastructure",
        "tools": [
            {"name": "list_vps", "description": "List all VPS instances"},
            {"name": "get_vps_status", "description": "Get VPS status and metrics"},
            {"name": "vps_action", "description": "Start/stop/restart/rebuild VPS"},
            {"name": "list_dns_zones", "description": "List DNS zones"},
            {"name": "manage_dns_records", "description": "Create/update/delete DNS records"},
            {"name": "list_domains", "description": "List registered domains"},
            {"name": "ssl_status", "description": "Check SSL certificate status"},
        ],
        "use_when": [
            "Managing VPS instances",
            "Configuring DNS records",
            "Checking server status",
            "SSL certificate management",
        ],
    },
    # cipher-memory tools
    {
        "name": "cipher-memory",
        "description": "Persistent Memory & Reasoning - Store and retrieve knowledge",
        "category": "memory",
        "tools": [
            {"name": "store_memory", "description": "Store information with tags"},
            {"name": "search_memory", "description": "Search stored memories"},
            {"name": "retrieve_memories", "description": "Get memories by filter"},
            {"name": "update_memory", "description": "Update existing memory"},
            {"name": "delete_memory", "description": "Remove memory by ID"},
        ],
        "use_when": [
            "Storing task context for later",
            "Remembering past solutions",
            "Cross-session knowledge persistence",
            "Learning from outcomes",
        ],
    },
    # e2b tools
    {
        "name": "e2b",
        "description": "E2B Code Sandbox - Execute code in isolated environments",
        "category": "execution",
        "tools": [
            {"name": "sandbox_run", "description": "Run code in sandbox"},
            {"name": "sandbox_exec", "description": "Execute command in sandbox"},
            {"name": "sandbox_stop", "description": "Stop running sandbox"},
        ],
        "use_when": [
            "Testing code safely",
            "Running user-provided code",
            "Executing untrusted scripts",
            "Isolated development",
        ],
    },
    # vl-sentinel tools
    {
        "name": "vl-sentinel",
        "description": "Vision-Language Guidance - Visual analysis and guidance",
        "category": "vision",
        "tools": [
            {"name": "vl_guide", "description": "Get visual guidance on images/screenshots"},
        ],
        "use_when": [
            "Analyzing UI screenshots",
            "Visual debugging",
            "Image-based guidance",
            "UI/UX feedback",
        ],
    },
    # docling tools
    {
        "name": "docling",
        "description": "Document Processing - Parse and extract from documents",
        "category": "documents",
        "tools": [
            {"name": "convert_document", "description": "Convert document to markdown/JSON"},
            {"name": "extract_tables", "description": "Extract tables from documents"},
        ],
        "use_when": [
            "Parsing PDF documents",
            "Extracting structured data",
            "Converting document formats",
            "Table extraction",
        ],
    },
    # postman tools
    {
        "name": "postman",
        "description": "API Testing & Collections - Manage and run API tests",
        "category": "api",
        "tools": [
            {"name": "run_collection", "description": "Run Postman collection"},
            {"name": "get_collection", "description": "Get collection details"},
            {"name": "list_collections", "description": "List available collections"},
        ],
        "use_when": [
            "Testing API endpoints",
            "Running API test suites",
            "Managing API collections",
            "API debugging",
        ],
    },
]


def store_to_cipher(content: str, tags: List[str]) -> str:
    """Store content in cipher memory via CLI."""
    cipher_path = os.environ.get(
        "CIPHER_PATH", "/app/features/cipher/pmoves_cipher/dist/src/app/index.cjs"
    )

    if not os.path.exists(cipher_path):
        # Try alternative paths
        alt_paths = [
            "/home/pmoves/PMOVES.AI/PMOVES-BoTZ/features/cipher/pmoves_cipher/dist/src/app/index.cjs",
            "./features/cipher/pmoves_cipher/dist/src/app/index.cjs",
        ]
        for alt in alt_paths:
            if os.path.exists(alt):
                cipher_path = alt
                break
        else:
            return f"[cipher not found] Would store: {content[:100]}..."

    try:
        cmd = ["node", cipher_path, "--mode", "cli", f"Store: {content}"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
    except Exception as e:
        return f"[cipher error] {e}"


def register_all_tools() -> None:
    """Register all BoTZ tools to cipher memory."""
    print("Registering BoTZ tools to cipher memory...")
    print("=" * 60)

    for tool_group in BOTZ_TOOLS:
        print(f"\nRegistering: {tool_group['name']}")

        # Create structured content
        content = f"""Tool Group: {tool_group['name']}
Category: {tool_group['category']}
Description: {tool_group['description']}

Available Tools:
{chr(10).join(f"- {t['name']}: {t['description']}" for t in tool_group['tools'])}

Use When:
{chr(10).join(f"- {u}" for u in tool_group['use_when'])}
"""

        tags = [
            "botz_tool",
            tool_group["category"],
            tool_group["name"],
            "mcp",
        ]

        result = store_to_cipher(content, tags)
        print(f"  Result: {result[:100]}...")

    print("\n" + "=" * 60)
    print("Registration complete!")


def main() -> None:
    """Main entry point."""
    register_all_tools()

    # Also output JSON for programmatic use
    output_file = os.environ.get("BOTZ_TOOLS_JSON", None)
    if output_file:
        with open(output_file, "w") as f:
            json.dump(BOTZ_TOOLS, f, indent=2)
        print(f"\nTool definitions saved to: {output_file}")


if __name__ == "__main__":
    main()
