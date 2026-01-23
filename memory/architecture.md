# PMOVES-BoTZ Architecture

## System Overview

PMOVES-BoTZ is a multi-agent orchestration framework implementing the "Codebase Singularity" doctrine. The system comprises:

1. **Agentic Layer** - AI agents managing the application
2. **Application Layer** - Core business logic (cipher, integrations)
3. **Infrastructure Layer** - Docker, databases, message queues

## Agent Hierarchy

```
                    ┌─────────────────┐
                    │   Orchestrator  │ (Opus 4.5)
                    │   "The Brain"   │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
    ┌───────▼───────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │    Builder    │ │   Auditor   │ │  Researcher │
    │  "The Hands"  │ │"The Conscience"│ │ "The Eyes" │
    │  (Sonnet)     │ │  (Haiku)    │ │  (Sonnet)   │
    └───────────────┘ └─────────────┘ └─────────────┘
```

## Thread Types Supported

| Type | Symbol | Description |
|------|--------|-------------|
| Base | B | Single prompt-response |
| Parallel | P | Multiple agents simultaneously |
| Chained | C | Sequential dependencies |
| Fusion | F | Multi-model consensus |
| Big | B | Orchestrated DAG |
| Zero Touch | Z | Fully autonomous |

## Directory Structure

```
PMOVES-BoTZ/
├── .mprocs.yaml          # Orchestration config
├── security/
│   └── patterns.yaml     # Security constitution
├── skills/
│   ├── botz-orchestrator/
│   ├── code-builder/
│   └── security-auditor/
├── memory/
│   ├── architecture.md   # This file
│   ├── status.md         # Current swarm state
│   ├── expertise/        # Learned knowledge
│   ├── audit/            # Action logs
│   └── plans/            # Thread plans
├── core/                 # Infrastructure configs
├── features/             # Feature modules
└── docs/                 # Documentation
```

## Security Model

- **Defense in Depth**: Multiple layers of protection
- **Principle of Least Privilege**: Minimal permissions per agent
- **Audit Trail**: All actions logged
- **Sandbox Execution**: Isolated environments for code execution

## Integration Points

- **MCP Servers**: Tool abstraction layer
- **NATS**: Message bus for agent communication
- **Venice.ai**: External AI API for large models
- **Docker Compose**: Service orchestration
