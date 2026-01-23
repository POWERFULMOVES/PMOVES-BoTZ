"""
Audit Hook

Logs all tool usage for security auditing and debugging.
Stores logs to file and optionally to Supabase.

Usage:
    # As a function
    await audit_tool_use(tool_name, input_data, result, agent_id)

    # As CLI (for hook command)
    python -m pmoves_botz.features.agent_sdk.hooks.audit --agent-id xxx --phase pre
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class AuditHook:
    """
    Audit hook for logging tool usage.

    Logs to:
    - Local file: ~/.pmoves/audit/tool_usage.jsonl
    - Supabase: agent_audit_logs table (if configured)

    Attributes:
        agent_id: Agent identifier
        log_dir: Directory for audit logs
        supabase_url: Supabase endpoint (optional)
    """

    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    LOG_DIR = Path(os.path.expanduser("~/.pmoves/audit"))

    def __init__(self, agent_id: str):
        """
        Initialize audit hook.

        Args:
            agent_id: Agent identifier for log attribution
        """
        self.agent_id = agent_id
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)

    async def pre_tool_use(
        self,
        tool_name: str,
        input_data: dict,
        context: Optional[dict] = None,
    ) -> dict:
        """
        Log before tool execution.

        Args:
            tool_name: Name of tool being called
            input_data: Tool input parameters
            context: Execution context

        Returns:
            Empty dict (no modification)
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "agent_id": self.agent_id,
            "phase": "pre",
            "tool_name": tool_name,
            "input_summary": self._summarize_input(input_data),
            "context_keys": list(context.keys()) if context else [],
        }

        await self._write_log(log_entry)
        return {}

    async def post_tool_use(
        self,
        tool_name: str,
        input_data: dict,
        result: Any,
        duration_ms: float,
        context: Optional[dict] = None,
    ) -> dict:
        """
        Log after tool execution.

        Args:
            tool_name: Name of tool called
            input_data: Tool input parameters
            result: Tool result
            duration_ms: Execution time
            context: Execution context

        Returns:
            Empty dict (no modification)
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "agent_id": self.agent_id,
            "phase": "post",
            "tool_name": tool_name,
            "input_summary": self._summarize_input(input_data),
            "result_type": type(result).__name__,
            "success": not self._is_error(result),
            "duration_ms": duration_ms,
        }

        await self._write_log(log_entry)
        return {}

    def _summarize_input(self, input_data: dict) -> dict:
        """
        Create a safe summary of input data (no secrets).

        Redacts sensitive fields recursively through nested structures.
        """
        # Sensitive key patterns to redact
        SENSITIVE_PATTERNS = [
            "password", "passwd", "pwd",
            "secret", "shared_secret",
            "token", "access_token", "refresh_token", "auth_token", "api_token",
            "key", "api_key", "apikey", "api_key", "private_key", "secret_key",
            "credential", "credentials",
            "authorization", "auth",
            "bearer",
        ]

        def _redact_value(value: Any) -> Any:
            """Recursively redact sensitive data from value."""
            if isinstance(value, dict):
                return _redact_dict(value)
            elif isinstance(value, list):
                return [_redact_item(item) for item in value]
            elif isinstance(value, str):
                # Redact strings that look like JWTs or API keys
                if len(value) > 30 and (
                    value.startswith("ey") or  # JWT
                    value.startswith("sk-") or  # OpenAI-style keys
                    value.startswith("xoxb") or  # Slack
                    len(value.split("-")) == 5  # UUID-like
                ):
                    return "[REDACTED_POSSIBLE_CREDENTIAL]"
                return value
            return value

        def _redact_item(item: Any) -> Any:
            """Redact a single item (could be dict, list, or primitive)."""
            if isinstance(item, dict):
                return _redact_dict(item)
            elif isinstance(item, list):
                return [_redact_item(i) for i in item]
            return item

        def _redact_dict(d: dict) -> dict:
            """Recursively redact sensitive keys in a dictionary."""
            result = {}
            for key, value in d.items():
                # Check if key matches any sensitive pattern
                key_lower = key.lower().replace("_", "").replace("-", "")
                is_sensitive = any(
                    pattern.replace("_", "").replace("-", "") in key_lower
                    for pattern in SENSITIVE_PATTERNS
                )

                if is_sensitive:
                    result[key] = "[REDACTED]"
                elif isinstance(value, (dict, list)):
                    result[key] = _redact_value(value)
                elif isinstance(value, str) and len(value) > 200:
                    result[key] = f"{value[:100]}... [{len(value)} chars]"
                else:
                    result[key] = value
            return result

        # Handle if input_data is not a dict
        if not isinstance(input_data, dict):
            return {"value": _redact_value(input_data)}

        return _redact_dict(input_data)

    def _is_error(self, result: Any) -> bool:
        """Check if result indicates an error."""
        if isinstance(result, dict):
            return "error" in result or result.get("success") is False
        return False

    async def _write_log(self, entry: dict) -> None:
        """Write log entry to file and optionally Supabase."""
        # Write to JSONL file
        log_file = self.LOG_DIR / "tool_usage.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

        # Write to Supabase if configured
        if self.SUPABASE_URL:
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{self.SUPABASE_URL}/rest/v1/agent_audit_logs",
                        json=entry,
                    )
            except Exception:
                pass  # Don't fail on logging errors


async def audit_tool_use(
    tool_name: str,
    input_data: dict,
    result: Any,
    agent_id: str,
    duration_ms: float = 0,
) -> None:
    """
    Convenience function to audit a tool use.

    Args:
        tool_name: Tool name
        input_data: Tool input
        result: Tool result
        agent_id: Agent ID
        duration_ms: Execution time
    """
    hook = AuditHook(agent_id)
    await hook.post_tool_use(tool_name, input_data, result, duration_ms)


def main():
    """CLI entry point for hook command."""
    parser = argparse.ArgumentParser(description="PMOVES Audit Hook")
    parser.add_argument("--agent-id", required=True, help="Agent identifier")
    parser.add_argument("--phase", choices=["pre", "post"], default="post")
    parser.add_argument("--tool", help="Tool name")

    args = parser.parse_args()

    # Read input from stdin (Claude Agent SDK passes JSON)
    input_json = sys.stdin.read() if not sys.stdin.isatty() else "{}"

    try:
        data = json.loads(input_json)
    except json.JSONDecodeError:
        data = {}

    # Create log entry
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "agent_id": args.agent_id,
        "phase": args.phase,
        "tool_name": args.tool or data.get("tool_name", "unknown"),
        "input_keys": list(data.get("input", {}).keys()) if data.get("input") else [],
    }

    # Write to log file
    log_dir = Path(os.path.expanduser("~/.pmoves/audit"))
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "tool_usage.jsonl"

    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    # Output empty JSON to indicate no modification
    print("{}")


if __name__ == "__main__":
    main()
