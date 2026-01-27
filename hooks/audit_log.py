# /// script
# requires-python = ">=3.8"
# dependencies = ["pyyaml"]
# ///
"""
PMOVES-BoTZ Audit Logger
=========================

Post-execution hook that logs all agent actions for audit trail.
Creates JSONL logs in memory/audit/ directory.

Usage:
  echo '{"tool_name": "Bash", "tool_input": {...}, "result": {...}}' | python audit_log.py

Reference: docs/agents/Aligning AI Agents with Indy Dev Dan.md
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

import yaml


def get_log_path() -> Path:
    """Get path to audit log directory."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    log_dir = Path(project_dir) / "memory" / "audit"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_agent_context() -> Dict[str, Any]:
    """Get current agent context from environment."""
    return {
        "agent_role": os.environ.get("BOTZ_AGENT_ROLE", "unknown"),
        "session_id": os.environ.get("BOTZ_SESSION_ID", "unknown"),
        "model": os.environ.get("BOTZ_MODEL", "unknown"),
        "working_dir": os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    }


def sanitize_content(content: Any, max_length: int = 500) -> Any:
    """Sanitize content for logging, truncating long strings."""
    if isinstance(content, str):
        if len(content) > max_length:
            return content[:max_length] + f"... [truncated, total {len(content)} chars]"
        return content
    elif isinstance(content, dict):
        return {k: sanitize_content(v, max_length) for k, v in content.items()}
    elif isinstance(content, list):
        return [sanitize_content(item, max_length) for item in content[:10]]  # Max 10 items
    return content


def log_action(
    tool_name: str,
    tool_input: Dict[str, Any],
    result: Optional[Dict[str, Any]] = None,
    status: str = "executed",
    security_decision: Optional[str] = None
) -> None:
    """Log an agent action to the audit log."""
    log_dir = get_log_path()
    log_file = log_dir / "agent_actions.jsonl"

    # Build log entry
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "tool": tool_name,
        "status": status,
        "agent": get_agent_context(),
        "input": sanitize_content(tool_input),
    }

    if result:
        entry["result"] = sanitize_content(result)

    if security_decision:
        entry["security_decision"] = security_decision

    # Add specific fields based on tool type
    if tool_name == "Bash":
        entry["command_preview"] = sanitize_content(tool_input.get("command", ""), 200)
    elif tool_name in ["Edit", "Write"]:
        entry["file_path"] = tool_input.get("file_path", "")
    elif tool_name == "Read":
        entry["file_path"] = tool_input.get("file_path", "")

    # Write to log file
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"Warning: Failed to write audit log: {e}", file=sys.stderr)


def main() -> None:
    """Main entry point for audit logger hook."""
    # Read input from stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        # No input, nothing to log
        sys.exit(0)
    except Exception as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        sys.exit(0)  # Don't fail the hook

    tool_name = input_data.get("tool_name", "unknown")
    tool_input = input_data.get("tool_input", {})
    result = input_data.get("result")
    status = input_data.get("status", "executed")
    security_decision = input_data.get("security_decision")

    log_action(tool_name, tool_input, result, status, security_decision)

    # Always exit 0 - audit logging should not block operations
    sys.exit(0)


if __name__ == "__main__":
    main()
