# /// script
# requires-python = ">=3.8"
# dependencies = ["pyyaml", "httpx"]
# ///
"""
PMOVES-BoTZ Probabilistic Prompt Scanner
=========================================

LLM-based semantic analysis for:
1. Detecting dangerous command patterns that regex might miss
2. Scanning prompts for injection attacks
3. Analyzing code for security vulnerabilities

Uses confidence thresholds to decide between:
- Allow (high confidence safe)
- Ask user (uncertain)
- Block (high confidence dangerous)

Exit codes:
  0 = Allow (with optional JSON for ask decision)
  2 = Block (high-confidence dangerous)

Usage:
  echo '{"content": "command here", "action_type": "shell_command"}' | python prompt_scan.py

Reference: docs/agents/Aligning AI Agents with Indy Dev Dan.md
"""

import json
import sys
import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

import yaml

# Try to import httpx for API calls, fall back gracefully
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class Verdict(Enum):
    """Possible verdicts from LLM evaluation."""
    SAFE = "safe"
    RISKY = "risky"
    BLOCK = "block"
    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    INJECTION = "injection"
    WARNING = "warning"
    UNSAFE = "unsafe"


@dataclass
class ScanResult:
    """Result of a probabilistic scan."""
    verdict: Verdict
    confidence: float
    reason: str
    pattern: Optional[str] = None
    issues: Optional[list] = None


# ============================================================================
# CONFIGURATION
# ============================================================================

def get_config_path() -> Path:
    """Get path to patterns.yaml."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        config = Path(project_dir) / "patterns.yaml"
        if config.exists():
            return config

    script_dir = Path(__file__).parent
    root_config = script_dir.parent / "patterns.yaml"
    if root_config.exists():
        return root_config

    security_config = script_dir.parent / "security" / "patterns.yaml"
    if security_config.exists():
        return security_config

    return root_config


def load_config() -> Dict[str, Any]:
    """Load configuration from patterns.yaml."""
    config_path = get_config_path()

    if not config_path.exists():
        logger.warning(f"Config not found at {config_path}")
        return {"probabilisticRules": []}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {}


# ============================================================================
# QUICK HEURISTIC CHECKS (No LLM needed)
# ============================================================================

# Known dangerous patterns that can be detected without LLM
INJECTION_PATTERNS = [
    # Prompt injection attempts
    (r"ignore\s+(previous|all|above)\s+instructions?", "ignore_instruction"),
    (r"disregard\s+(previous|all|above)", "disregard_instruction"),
    (r"forget\s+(everything|all|your)\s+(instructions?|rules?)", "forget_instruction"),
    (r"you\s+are\s+now\s+(a|an|the)", "role_override"),
    (r"pretend\s+(to\s+be|you\s+are)", "role_play"),
    (r"act\s+as\s+(if|a|an|the)", "role_play"),
    (r"new\s+system\s+prompt", "system_override"),
    (r"override\s+(system|safety)", "system_override"),
    (r"jailbreak", "jailbreak_attempt"),
    (r"DAN\s+mode", "jailbreak_attempt"),
    (r"developer\s+mode", "developer_mode"),
    (r"admin\s+mode", "admin_mode"),

    # Encoded content (potential obfuscation)
    (r"base64[:\s]", "encoded_content"),
    (r"\\x[0-9a-fA-F]{2}", "hex_encoded"),
    (r"\\u[0-9a-fA-F]{4}", "unicode_encoded"),

    # Data exfiltration patterns
    (r"curl.*-d.*@", "data_exfiltration"),
    (r"curl.*--data.*@", "data_exfiltration"),
    (r"wget.*--post-file", "data_exfiltration"),
    (r"nc\s+.*<", "netcat_redirect"),
]

# Patterns in commands that suggest dangerous operations
DANGEROUS_COMMAND_PATTERNS = [
    # Credential/secret access
    (r"cat\s+.*\.env", "env_file_read"),
    (r"cat\s+.*/\.ssh/", "ssh_key_read"),
    (r"cat\s+.*credentials", "credential_read"),
    (r"cat\s+.*secret", "secret_read"),
    (r"echo\s+\$\{?[A-Z_]*KEY", "key_echo"),
    (r"echo\s+\$\{?[A-Z_]*SECRET", "secret_echo"),
    (r"echo\s+\$\{?[A-Z_]*TOKEN", "token_echo"),
    (r"echo\s+\$\{?[A-Z_]*PASSWORD", "password_echo"),

    # History manipulation
    (r"history\s*-[cd]", "history_manipulation"),
    (r"unset\s+HISTFILE", "history_disable"),
    (r"export\s+HISTSIZE=0", "history_disable"),

    # Network exfiltration
    (r"curl\s+.*\|\s*tee", "curl_tee"),
    (r"wget\s+.*\|\s*tee", "wget_tee"),
    (r"/dev/tcp/", "bash_socket"),
    (r"/dev/udp/", "bash_socket"),

    # Privilege escalation
    (r"sudo\s+-i", "sudo_interactive"),
    (r"su\s+-\s*$", "switch_user"),
    (r"chmod\s+[47]755", "setuid_bit"),
    (r"chmod\s+u\+s", "setuid_bit"),

    # Container escape
    (r"docker\s+run.*--privileged", "privileged_container"),
    (r"docker\s+run.*-v\s+/:/", "root_mount"),
    (r"nsenter", "namespace_escape"),
]


def quick_heuristic_check(content: str, action_type: str) -> Optional[ScanResult]:
    """
    Perform quick heuristic checks without LLM.
    Returns ScanResult if a pattern matches, None otherwise.
    """
    content_lower = content.lower()

    # Check injection patterns for prompts
    if action_type in ["user_prompt", "external_input"]:
        for pattern, name in INJECTION_PATTERNS:
            if re.search(pattern, content_lower, re.IGNORECASE):
                return ScanResult(
                    verdict=Verdict.SUSPICIOUS,
                    confidence=0.75,
                    reason=f"Potential prompt injection detected",
                    pattern=name
                )

    # Check dangerous patterns for commands
    if action_type in ["shell_command", "bash"]:
        for pattern, name in DANGEROUS_COMMAND_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                return ScanResult(
                    verdict=Verdict.RISKY,
                    confidence=0.80,
                    reason=f"Potentially dangerous command pattern: {name}",
                    pattern=name
                )

    return None


# ============================================================================
# LLM EVALUATION
# ============================================================================

def get_llm_client() -> Optional[Any]:
    """Get HTTP client for LLM API calls."""
    if not HTTPX_AVAILABLE:
        logger.warning("httpx not available, LLM evaluation disabled")
        return None

    return httpx.Client(timeout=30.0)


def call_llm(
    client: Any,
    model: str,
    prompt: str,
    content: str,
    action_type: str,
    working_dir: str = ""
) -> Optional[Dict[str, Any]]:
    """
    Call LLM API for evaluation.

    Supports:
    - TensorZero (TENSORZERO_BASE_URL)
    - Anthropic API (ANTHROPIC_API_KEY)
    - OpenAI-compatible (OPENAI_API_KEY, OPENAI_BASE_URL)
    """
    # Format the prompt
    formatted_prompt = prompt.format(
        content=content,
        action_type=action_type,
        working_dir=working_dir or os.getcwd(),
        language="unknown"  # For code analysis
    )

    # Try TensorZero first
    tensorzero_url = os.environ.get("TENSORZERO_BASE_URL", "http://localhost:3030")
    try:
        response = client.post(
            f"{tensorzero_url}/v1/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "user", "content": formatted_prompt}],
                "temperature": 0.0,
                "max_tokens": 200
            },
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.debug(f"TensorZero call failed: {e}")

    # Try Anthropic API
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_key:
        try:
            response = client.post(
                "https://api.anthropic.com/v1/messages",
                json={
                    "model": model,
                    "max_tokens": 200,
                    "messages": [{"role": "user", "content": formatted_prompt}]
                },
                headers={
                    "x-api-key": anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                }
            )
            if response.status_code == 200:
                data = response.json()
                # Convert to OpenAI-like format
                return {
                    "choices": [{
                        "message": {
                            "content": data.get("content", [{}])[0].get("text", "")
                        }
                    }]
                }
        except Exception as e:
            logger.debug(f"Anthropic API call failed: {e}")

    # Try OpenAI-compatible
    openai_key = os.environ.get("OPENAI_API_KEY")
    openai_base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    if openai_key:
        try:
            response = client.post(
                f"{openai_base}/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": formatted_prompt}],
                    "temperature": 0.0,
                    "max_tokens": 200
                },
                headers={
                    "Authorization": f"Bearer {openai_key}",
                    "Content-Type": "application/json"
                }
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"OpenAI API call failed: {e}")

    return None


def parse_llm_response(response_text: str) -> ScanResult:
    """Parse LLM response into structured ScanResult."""
    lines = response_text.strip().split('\n')

    verdict = Verdict.SAFE
    confidence = 0.5
    reason = ""
    pattern = None
    issues = []

    for line in lines:
        line = line.strip()
        if line.upper().startswith("VERDICT:"):
            verdict_str = line.split(":", 1)[1].strip().upper()
            # Map various verdicts
            verdict_map = {
                "SAFE": Verdict.SAFE,
                "RISKY": Verdict.RISKY,
                "BLOCK": Verdict.BLOCK,
                "CLEAN": Verdict.CLEAN,
                "SUSPICIOUS": Verdict.SUSPICIOUS,
                "INJECTION": Verdict.INJECTION,
                "WARNING": Verdict.WARNING,
                "UNSAFE": Verdict.UNSAFE
            }
            verdict = verdict_map.get(verdict_str, Verdict.RISKY)

        elif line.upper().startswith("CONFIDENCE:"):
            try:
                conf_str = line.split(":", 1)[1].strip()
                confidence = float(conf_str)
            except ValueError:
                confidence = 0.5

        elif line.upper().startswith("REASON:"):
            reason = line.split(":", 1)[1].strip()

        elif line.upper().startswith("PATTERN:"):
            pattern = line.split(":", 1)[1].strip()

        elif line.upper().startswith("ISSUES:"):
            issues_str = line.split(":", 1)[1].strip()
            if issues_str.startswith("["):
                try:
                    issues = json.loads(issues_str)
                except:
                    issues = [issues_str]
            else:
                issues = [issues_str]

    return ScanResult(
        verdict=verdict,
        confidence=confidence,
        reason=reason,
        pattern=pattern,
        issues=issues if issues else None
    )


def evaluate_with_llm(
    content: str,
    action_type: str,
    rule: Dict[str, Any],
    working_dir: str = ""
) -> Optional[ScanResult]:
    """Evaluate content using LLM based on rule configuration."""
    if not rule.get("enabled", True):
        return None

    model = rule.get("model", "claude-3-haiku-20240307")
    prompt = rule.get("prompt", "")

    if not prompt:
        return None

    client = get_llm_client()
    if not client:
        logger.warning("No LLM client available for probabilistic evaluation")
        return None

    try:
        response = call_llm(client, model, prompt, content, action_type, working_dir)

        if response and "choices" in response:
            response_text = response["choices"][0]["message"]["content"]
            result = parse_llm_response(response_text)

            # Check confidence threshold
            threshold = rule.get("confidence_threshold", 0.85)
            if result.confidence < threshold and result.verdict in [Verdict.SAFE, Verdict.CLEAN]:
                # Low confidence safe - treat as uncertain
                return ScanResult(
                    verdict=Verdict.RISKY,
                    confidence=result.confidence,
                    reason=f"Low confidence ({result.confidence:.2f}) in safe verdict - requires review"
                )

            return result

    except Exception as e:
        logger.error(f"LLM evaluation failed: {e}")

    # Fallback model if primary fails
    fallback_model = rule.get("fallback_model")
    if fallback_model and fallback_model != model:
        try:
            response = call_llm(client, fallback_model, prompt, content, action_type, working_dir)
            if response and "choices" in response:
                response_text = response["choices"][0]["message"]["content"]
                return parse_llm_response(response_text)
        except Exception as e:
            logger.error(f"Fallback LLM evaluation failed: {e}")

    return None


# ============================================================================
# LOGGING
# ============================================================================

def log_scan_result(
    content: str,
    action_type: str,
    result: ScanResult,
    source: str = "heuristic"
) -> None:
    """Log scan result for audit trail."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "action_type": action_type,
        "source": source,
        "verdict": result.verdict.value,
        "confidence": result.confidence,
        "reason": result.reason,
        "pattern": result.pattern,
        "content_preview": content[:100] + "..." if len(content) > 100 else content
    }

    # Log to file if configured
    log_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")) / "memory" / "audit"
    if log_dir.exists():
        log_file = log_dir / "prompt_scan.jsonl"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.warning(f"Failed to write to log file: {e}")

    # Always log to stderr at appropriate level
    if result.verdict in [Verdict.BLOCK, Verdict.INJECTION, Verdict.UNSAFE]:
        logger.warning(f"BLOCKED: {json.dumps(log_entry)}")
    elif result.verdict in [Verdict.RISKY, Verdict.SUSPICIOUS, Verdict.WARNING]:
        logger.info(f"FLAGGED: {json.dumps(log_entry)}")
    else:
        logger.debug(f"ALLOWED: {json.dumps(log_entry)}")


# ============================================================================
# MAIN SCAN FUNCTION
# ============================================================================

def scan(content: str, action_type: str, config: Dict[str, Any]) -> ScanResult:
    """
    Main scan function that combines heuristic and LLM evaluation.

    Returns final ScanResult with verdict and confidence.
    """
    working_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    # 1. Quick heuristic check first (fast, no LLM cost)
    heuristic_result = quick_heuristic_check(content, action_type)
    if heuristic_result:
        log_scan_result(content, action_type, heuristic_result, "heuristic")

        # If high-confidence block, return immediately
        if heuristic_result.verdict in [Verdict.BLOCK, Verdict.INJECTION]:
            return heuristic_result

        # If heuristic flagged something, still run LLM for confirmation
        # unless confidence is very high
        if heuristic_result.confidence >= 0.90:
            return heuristic_result

    # 2. Find applicable probabilistic rules
    probabilistic_rules = config.get("probabilisticRules", [])

    for rule in probabilistic_rules:
        if not rule.get("enabled", True):
            continue

        # Check if this rule applies to the action type
        triggers = rule.get("trigger_on", [])
        if action_type not in triggers and "all" not in triggers:
            continue

        # Evaluate with LLM
        llm_result = evaluate_with_llm(content, action_type, rule, working_dir)

        if llm_result:
            log_scan_result(content, action_type, llm_result, f"llm:{rule.get('name', 'unknown')}")

            # If LLM flags as dangerous, return that result
            if llm_result.verdict in [Verdict.BLOCK, Verdict.INJECTION, Verdict.UNSAFE]:
                return llm_result

            # If LLM flags as risky/suspicious, return for user review
            if llm_result.verdict in [Verdict.RISKY, Verdict.SUSPICIOUS, Verdict.WARNING]:
                # Combine with heuristic result if available
                if heuristic_result:
                    # Take the more cautious verdict
                    combined_confidence = max(heuristic_result.confidence, llm_result.confidence)
                    combined_reason = f"{heuristic_result.reason}; {llm_result.reason}"
                    return ScanResult(
                        verdict=llm_result.verdict,
                        confidence=combined_confidence,
                        reason=combined_reason,
                        pattern=heuristic_result.pattern or llm_result.pattern,
                        issues=llm_result.issues
                    )
                return llm_result

    # 3. If heuristic flagged but LLM didn't run or found safe
    if heuristic_result and heuristic_result.verdict not in [Verdict.SAFE, Verdict.CLEAN]:
        return heuristic_result

    # 4. Default: allow
    return ScanResult(
        verdict=Verdict.SAFE,
        confidence=1.0,
        reason="No dangerous patterns detected"
    )


# ============================================================================
# MAIN
# ============================================================================

def main() -> None:
    """Main entry point for prompt scanner."""
    config = load_config()

    # Read input from stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error reading input: {e}")
        sys.exit(1)

    # Extract content and action type
    content = input_data.get("content", "")
    action_type = input_data.get("action_type", "unknown")

    # For Bash tool integration
    if not content:
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        if tool_name == "Bash":
            content = tool_input.get("command", "")
            action_type = "shell_command"
        elif tool_name in ["Edit", "Write"]:
            content = tool_input.get("new_string", "") or tool_input.get("content", "")
            action_type = "code_modification"
        elif tool_name == "user_message":
            content = tool_input.get("text", "")
            action_type = "user_prompt"

    if not content:
        # Nothing to scan
        sys.exit(0)

    # Run scan
    result = scan(content, action_type, config)

    # Determine action based on verdict
    action_map = {
        Verdict.SAFE: "allow",
        Verdict.CLEAN: "allow",
        Verdict.RISKY: "ask_user",
        Verdict.SUSPICIOUS: "log_and_allow",
        Verdict.WARNING: "allow_with_log",
        Verdict.BLOCK: "deny",
        Verdict.INJECTION: "deny",
        Verdict.UNSAFE: "ask_user"
    }

    action = action_map.get(result.verdict, "allow")

    # Output decision
    if action == "deny":
        print(f"SECURITY BLOCK: {result.reason}", file=sys.stderr)
        if result.pattern:
            print(f"Pattern: {result.pattern}", file=sys.stderr)
        print(f"Confidence: {result.confidence:.2f}", file=sys.stderr)
        sys.exit(2)

    elif action == "ask_user":
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": f"[SECURITY] {result.reason} (confidence: {result.confidence:.2f})"
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    elif action in ["log_and_allow", "allow_with_log"]:
        # Log but allow
        logger.info(f"Suspicious but allowed: {result.reason}")
        sys.exit(0)

    else:
        # Allow
        sys.exit(0)


if __name__ == "__main__":
    main()
