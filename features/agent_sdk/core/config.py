"""
Core Configuration - Environment-based configuration loading.
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Config:
    """Configuration container for PMOVES Agent SDK."""

    # Service URLs
    tensorzero_url: str = "http://localhost:3030"
    hirag_url: str = "http://localhost:8086"
    nats_url: str = "nats://nats:pmoves@localhost:4222"
    supabase_url: str = "http://localhost:3010"
    gateway_url: str = "http://localhost:2091"

    # Agent settings
    agent_name: str = "pmoves-agent"
    default_model: str = "openai::qwen3:8b"
    max_workers: int = 4

    # Timeouts (seconds)
    http_timeout: int = 30
    task_timeout: int = 300

    # Feature flags
    enable_nats: bool = True
    enable_hooks: bool = True
    enable_a2a: bool = True

    # Custom settings
    custom: Dict[str, Any] = field(default_factory=dict)


def load_config(env_prefix: str = "PMOVES_") -> Config:
    """
    Load configuration from environment variables.

    Args:
        env_prefix: Prefix for environment variables (default: PMOVES_)

    Returns:
        Config instance with values from environment
    """
    def get_env(key: str, default: Any = None) -> Any:
        return os.environ.get(f"{env_prefix}{key}", default)

    return Config(
        tensorzero_url=get_env("TENSORZERO_URL", Config.tensorzero_url),
        hirag_url=get_env("HIRAG_URL", Config.hirag_url),
        nats_url=get_env("NATS_URL", Config.nats_url),
        supabase_url=get_env("SUPABASE_URL", Config.supabase_url),
        gateway_url=get_env("GATEWAY_URL", Config.gateway_url),
        agent_name=get_env("AGENT_NAME", Config.agent_name),
        default_model=get_env("DEFAULT_MODEL", Config.default_model),
        max_workers=int(get_env("MAX_WORKERS", Config.max_workers)),
        http_timeout=int(get_env("HTTP_TIMEOUT", Config.http_timeout)),
        task_timeout=int(get_env("TASK_TIMEOUT", Config.task_timeout)),
        enable_nats=get_env("ENABLE_NATS", "true").lower() == "true",
        enable_hooks=get_env("ENABLE_HOOKS", "true").lower() == "true",
        enable_a2a=get_env("ENABLE_A2A", "true").lower() == "true",
    )
