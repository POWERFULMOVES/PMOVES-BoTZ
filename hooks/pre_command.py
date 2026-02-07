# /// script
# requires-python = ">=3.8"
# dependencies = ["pyyaml"]
# ///
"""
PMOVES-BoTZ Pre-Command Security Hook
======================================

Pre-execution validation that:
1. Loads patterns.yaml configuration
2. Validates commands against deterministic regex rules
3. Checks path protection rules (zero-access, read-only, no-delete)
4. Returns allow/deny/ask decision

Exit codes:
  0 = Allow command (with optional JSON for ask decision)
  2 = Block command (stderr contains reason)

JSON output for ask patterns:
  {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permissionDecisionReason": "..."}}

Usage:
  echo '{"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}' | python pre_command.py

Reference: docs/agents/Aligning AI Agents with Indy Dev Dan.md
"""

import json
import sys
import re
import os
import fnmatch
import logging
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional
from datetime import datetime

import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)


# ============================================================================
# OPERATION PATTERNS - For path-based protection
# ============================================================================

# Operations blocked for READ-ONLY paths (all modifications)
WRITE_PATTERNS = [
    (r'>\s*{path}', "write"),
    (r'\btee\s+(?!.*-a).*{path}', "write"),
]

APPEND_PATTERNS = [
    (r'>>\s*{path}', "append"),
    (r'\btee\s+-a\s+.*{path}', "append"),
    (r'\btee\s+.*-a.*{path}', "append"),
]

EDIT_PATTERNS = [
    (r'\bsed\s+-i.*{path}', "edit"),
    (r'\bperl\s+-[^\s]*i.*{path}', "edit"),
    (r'\bawk\s+-i\s+inplace.*{path}', "edit"),
    (r'\bvim\s+.*{path}', "edit"),
    (r'\bnano\s+.*{path}', "edit"),
]

MOVE_COPY_PATTERNS = [
    (r'\bmv\s+.*\s+{path}', "move"),
    (r'\bcp\s+.*\s+{path}', "copy"),
]

DELETE_PATTERNS = [
    (r'\brm\s+.*{path}', "delete"),
    (r'\bunlink\s+.*{path}', "delete"),
    (r'\brmdir\s+.*{path}', "delete"),
    (r'\bshred\s+.*{path}', "delete"),
]

PERMISSION_PATTERNS = [
    (r'\bchmod\s+.*{path}', "chmod"),
    (r'\bchown\s+.*{path}', "chown"),
    (r'\bchgrp\s+.*{path}', "chgrp"),
]

TRUNCATE_PATTERNS = [
    (r'\btruncate\s+.*{path}', "truncate"),
    (r':\s*>\s*{path}', "truncate"),
]

# Combined patterns for read-only paths (block ALL modifications)
READ_ONLY_BLOCKED = (
    WRITE_PATTERNS +
    APPEND_PATTERNS +
    EDIT_PATTERNS +
    MOVE_COPY_PATTERNS +
    DELETE_PATTERNS +
    PERMISSION_PATTERNS +
    TRUNCATE_PATTERNS
)

# Patterns for no-delete paths (block ONLY delete operations)
NO_DELETE_BLOCKED = DELETE_PATTERNS


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def is_glob_pattern(pattern: str) -> bool:
    """Check if pattern contains glob wildcards."""
    return '*' in pattern or '?' in pattern or '[' in pattern


def glob_to_regex(glob_pattern: str) -> str:
    """Convert a glob pattern to a regex pattern for matching in commands."""
    result = ""
    i = 0
    while i < len(glob_pattern):
        char = glob_pattern[i]
        if char == '*':
            if i + 1 < len(glob_pattern) and glob_pattern[i + 1] == '*':
                # ** matches any path including separators
                result += r'.*'
                i += 2
                continue
            else:
                # * matches any chars except path separator
                result += r'[^\s/\\]*'
        elif char == '?':
            result += r'[^\s/\\]'
        elif char in r'\.^$+{}[]|()':
            result += '\\' + char
        else:
            result += char
        i += 1
    return result


def get_config_path() -> Path:
    """Get path to patterns.yaml, checking multiple locations."""
    # 1. Check CLAUDE_PROJECT_DIR environment variable
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        project_config = Path(project_dir) / "patterns.yaml"
        if project_config.exists():
            return project_config
        # Also check security subdirectory
        security_config = Path(project_dir) / "security" / "patterns.yaml"
        if security_config.exists():
            return security_config

    # 2. Check script's parent directory (hooks/../patterns.yaml)
    script_dir = Path(__file__).parent
    root_config = script_dir.parent / "patterns.yaml"
    if root_config.exists():
        return root_config

    # 3. Check security directory
    security_config = script_dir.parent / "security" / "patterns.yaml"
    if security_config.exists():
        return security_config

    # 4. Check .claude/hooks/damage-control (for compatibility)
    damage_control = script_dir.parent / ".claude" / "hooks" / "damage-control" / "patterns.yaml"
    if damage_control.exists():
        return damage_control

    return root_config  # Default, even if it doesn't exist


def load_config() -> Dict[str, Any]:
    """Load patterns from YAML config file."""
    config_path = get_config_path()

    if not config_path.exists():
        logger.warning(f"Config not found at {config_path}")
        return {
            "bashToolPatterns": [],
            "zeroAccessPaths": [],
            "readOnlyPaths": [],
            "noDeletePaths": [],
            "sqlPatterns": []
        }

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        logger.debug(f"Loaded config from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {}


# ============================================================================
# PATH CHECKING
# ============================================================================

def check_path_patterns(
    command: str,
    path: str,
    patterns: List[Tuple[str, str]],
    path_type: str
) -> Tuple[bool, str]:
    """
    Check command against a list of patterns for a specific path.

    Supports both:
    - Literal paths: ~/.bashrc, /etc/hosts (prefix matching)
    - Glob patterns: *.lock, *.md, src/* (glob matching)
    """
    if is_glob_pattern(path):
        # Glob pattern - convert to regex for command matching
        glob_regex = glob_to_regex(path)
        for pattern_template, operation in patterns:
            try:
                # Build a regex that matches: operation ... glob_pattern
                cmd_prefix = pattern_template.replace("{path}", "")
                if cmd_prefix and re.search(cmd_prefix + glob_regex, command, re.IGNORECASE):
                    return True, f"Blocked: {operation} operation on {path_type} {path}"
            except re.error:
                continue
    else:
        # Original literal path matching (prefix-based)
        expanded = os.path.expanduser(path)
        escaped_expanded = re.escape(expanded)
        escaped_original = re.escape(path)

        for pattern_template, operation in patterns:
            pattern_expanded = pattern_template.replace("{path}", escaped_expanded)
            pattern_original = pattern_template.replace("{path}", escaped_original)
            try:
                if re.search(pattern_expanded, command) or re.search(pattern_original, command):
                    return True, f"Blocked: {operation} operation on {path_type} {path}"
            except re.error:
                continue

    return False, ""


def match_path_in_command(command: str, pattern: str) -> bool:
    """Check if a path pattern appears in a command."""
    if is_glob_pattern(pattern):
        glob_regex = glob_to_regex(pattern)
        try:
            return bool(re.search(glob_regex, command, re.IGNORECASE))
        except re.error:
            return False
    else:
        expanded = os.path.expanduser(pattern)
        escaped_expanded = re.escape(expanded)
        escaped_original = re.escape(pattern)
        return bool(
            re.search(escaped_expanded, command) or
            re.search(escaped_original, command)
        )


# ============================================================================
# MAIN CHECK FUNCTION
# ============================================================================

def check_command(command: str, config: Dict[str, Any]) -> Tuple[bool, bool, str, str]:
    """
    Check if command should be blocked or requires confirmation.

    Returns: (blocked, ask, reason, severity)
      - blocked=True, ask=False: Block the command
      - blocked=False, ask=True: Show confirmation dialog
      - blocked=False, ask=False: Allow the command
    """
    patterns = config.get("bashToolPatterns", [])
    zero_access_paths = config.get("zeroAccessPaths", [])
    read_only_paths = config.get("readOnlyPaths", [])
    no_delete_paths = config.get("noDeletePaths", [])
    sql_patterns = config.get("sqlPatterns", [])

    # 1. Check against bash patterns from YAML (may block or ask)
    for item in patterns:
        pattern = item.get("pattern", "")
        reason = item.get("reason", "Blocked by pattern")
        should_ask = item.get("ask", False)
        severity = item.get("severity", "medium")
        case_insensitive = item.get("case_insensitive", False)

        flags = re.IGNORECASE if case_insensitive else 0

        try:
            if re.search(pattern, command, flags):
                if should_ask:
                    return False, True, reason, severity
                else:
                    return True, False, reason, severity
        except re.error as e:
            logger.warning(f"Invalid regex pattern '{pattern}': {e}")
            continue

    # 2. Check for ANY access to zero-access paths (including reads)
    for zero_path in zero_access_paths:
        if match_path_in_command(command, zero_path):
            return True, False, f"Zero-access path violation: {zero_path}", "critical"

    # 3. Check for modifications to read-only paths (reads allowed)
    for readonly in read_only_paths:
        blocked, reason = check_path_patterns(command, readonly, READ_ONLY_BLOCKED, "read-only")
        if blocked:
            return True, False, reason, "high"

    # 4. Check for deletions on no-delete paths (read/write/edit allowed)
    for no_delete in no_delete_paths:
        blocked, reason = check_path_patterns(command, no_delete, NO_DELETE_BLOCKED, "no-delete")
        if blocked:
            return True, False, reason, "high"

    # 5. Check SQL patterns if command contains SQL keywords
    sql_keywords = ["SELECT", "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"]
    command_upper = command.upper()
    if any(kw in command_upper for kw in sql_keywords):
        for item in sql_patterns:
            pattern = item.get("pattern", "")
            reason = item.get("reason", "SQL operation requires review")
            allowed_condition = item.get("allowedCondition", "")
            should_ask = item.get("ask", True)
            severity = item.get("severity", "medium")

            try:
                if re.search(pattern, command, re.IGNORECASE):
                    # Check if allowed condition is met
                    if allowed_condition and re.search(allowed_condition, command, re.IGNORECASE):
                        continue  # Allowed
                    if should_ask:
                        return False, True, reason, severity
                    else:
                        return True, False, reason, severity
            except re.error:
                continue

    return False, False, "", ""


def check_file_operation(
    tool_name: str,
    tool_input: Dict[str, Any],
    config: Dict[str, Any]
) -> Tuple[bool, bool, str, str]:
    """
    Check file operations (Edit, Write, Read) against path protection rules.

    Returns: (blocked, ask, reason, severity)
    """
    file_path = tool_input.get("file_path", "")
    if not file_path:
        return False, False, "", ""

    zero_access_paths = config.get("zeroAccessPaths", [])
    read_only_paths = config.get("readOnlyPaths", [])
    no_delete_paths = config.get("noDeletePaths", [])

    # Normalize path
    normalized = os.path.normpath(file_path)

    def match_path(check_path: str, pattern: str) -> bool:
        """Match a file path against a pattern."""
        expanded_pattern = os.path.expanduser(pattern)
        expanded_check = os.path.expanduser(check_path)

        if is_glob_pattern(pattern):
            basename = os.path.basename(expanded_check)
            # Try basename match
            if fnmatch.fnmatch(basename.lower(), pattern.lower()):
                return True
            if fnmatch.fnmatch(basename.lower(), expanded_pattern.lower()):
                return True
            # Try full path match
            if fnmatch.fnmatch(expanded_check.lower(), expanded_pattern.lower()):
                return True
            return False
        else:
            # Prefix matching
            return (
                expanded_check.startswith(expanded_pattern) or
                expanded_check == expanded_pattern.rstrip('/')
            )

    # Check zero-access (no read, write, or anything)
    for zero_path in zero_access_paths:
        if match_path(normalized, zero_path):
            return True, False, f"Zero-access path: {zero_path}", "critical"

    # Check read-only (only for write operations)
    if tool_name in ["Edit", "Write"]:
        for readonly in read_only_paths:
            if match_path(normalized, readonly):
                return True, False, f"Read-only path: {readonly}", "high"

    # Note: no-delete is checked via bash command patterns for rm operations

    return False, False, "", ""


# ============================================================================
# MAIN
# ============================================================================

def main() -> None:
    """Main entry point for pre-command hook."""
    config = load_config()

    # Read hook input from stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error reading input: {e}")
        sys.exit(1)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Check based on tool type
    is_blocked = False
    should_ask = False
    reason = ""
    severity = ""

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if command:
            is_blocked, should_ask, reason, severity = check_command(command, config)

    elif tool_name in ["Edit", "Write", "Read"]:
        is_blocked, should_ask, reason, severity = check_file_operation(
            tool_name, tool_input, config
        )

    # Log the decision
    if is_blocked or should_ask:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "tool": tool_name,
            "decision": "blocked" if is_blocked else "ask",
            "reason": reason,
            "severity": severity,
        }
        if tool_name == "Bash":
            cmd = tool_input.get("command", "")
            log_entry["command_preview"] = cmd[:100] + "..." if len(cmd) > 100 else cmd
        else:
            log_entry["file_path"] = tool_input.get("file_path", "")

        logger.info(f"Security decision: {json.dumps(log_entry)}")

    # Output decision
    if is_blocked:
        print(f"SECURITY [{severity.upper()}]: {reason}", file=sys.stderr)
        if tool_name == "Bash":
            cmd = tool_input.get("command", "")
            print(f"Command: {cmd[:100]}{'...' if len(cmd) > 100 else ''}", file=sys.stderr)
        else:
            print(f"File: {tool_input.get('file_path', '')}", file=sys.stderr)
        sys.exit(2)

    elif should_ask:
        # Output JSON to trigger confirmation dialog
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": f"[{severity.upper()}] {reason}"
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    else:
        # Allow
        sys.exit(0)


if __name__ == "__main__":
    main()
