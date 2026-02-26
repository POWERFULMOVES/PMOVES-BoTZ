# PMOVES.AI Tier Environment: Agent
# For Agent and Orchestrator services (Agent Zero, Archon, etc.)
# Docker env_file format — use with docker compose env_file directive

# ============================================================================
# Agent Tier Configuration
# ============================================================================

TIER=agent

# Agent limits
MAX_CONCURRENT_AGENTS=${MAX_CONCURRENT_AGENTS:-50}
MAX_TASKS_PER_AGENT=${MAX_TASKS_PER_AGENT:-10}
AGENT_TIMEOUT_MS=${AGENT_TIMEOUT_MS:-300000}  # 5 minutes
AGENT_IDLE_TIMEOUT_MS=${AGENT_IDLE_TIMEOUT_MS:-60000}  # 1 minute

# Task queue configuration
TASK_QUEUE_SIZE=${TASK_QUEUE_SIZE:-1000}
TASK_RETRY_MAX=${TASK_RETRY_MAX:-3}
TASK_RETRY_DELAY_MS=${TASK_RETRY_DELAY_MS:-1000}

# Tool execution
TOOL_TIMEOUT_MS=${TOOL_TIMEOUT_MS:-60000}  # 1 minute
MAX_TOOL_OUTPUT_SIZE=${MAX_TOOL_OUTPUT_SIZE:-1048576}  # 1MB

# MCP (Model Context Protocol) configuration
MCP_ENABLED=${MCP_ENABLED:-true}
MCP_TIMEOUT_MS=${MCP_TIMEOUT_MS:-30000}
MCP_MAX_MESSAGE_SIZE=${MCP_MAX_MESSAGE_SIZE:-10485760}  # 10MB

# Agent state persistence
STATE_PERSISTENCE_ENABLED=${STATE_PERSISTENCE_ENABLED:-true}
STATE_BACKEND=${STATE_BACKEND:-supabase}  # supabase | memory | file

# LLM configuration for agents
DEFAULT_MODEL=${DEFAULT_MODEL:-claude-sonnet-4-5}
DEFAULT_TEMPERATURE=${DEFAULT_TEMPERATURE:-0.7}
DEFAULT_MAX_TOKENS=${DEFAULT_MAX_TOKENS:-4096}

# Prompt management
PROMPT_CACHE_ENABLED=${PROMPT_CACHE_ENABLED:-true}
PROMPT_CACHE_SIZE=${PROMPT_CACHE_SIZE:-1000}
PROMPT_CACHE_TTL=${PROMPT_CACHE_TTL:-3600}  # 1 hour

# Archon-specific (if using Archon)
ARCHON_PROMPT_BACKEND=${ARCHON_PROMPT_BACKEND:-supabase}
ARCHON_FORM_SCHEMA_PATH=${ARCHON_FORM_SCHEMA_PATH:-/forms}
