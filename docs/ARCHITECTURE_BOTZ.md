# PMOVES-BoTZ Architecture Guide

**Edition:** BoTZ (Refactored Lite Edition)
**Status:** Active / Production-Ready

## 1. Overview
PMOVES-BoTZ is a streamlined, agentic AI platform designed for modularity and ease of deployment. Unlike the upstream "Reference Enterprise" architecture, BoTZ focuses on a lightweight orchestrator-worker model using `docker-compose`.

## 2. Directory Structure
The repository follows a strict "Single Source of Truth" layout:

```text
PMOVES-BoTZ/
├── core/                       # Core platform configuration
│   ├── docker-compose/        # Modular compose files
│   │   ├── base.yml          # MAIN ENTRYPOINT (Services)
│   │   └── overlays/         # Dev/Prod overrides
│   └── mcp/                   # MCP Gateway config
│       ├── catalog.yml       # Tool definitions
│       └── modes/            # Agent personalities
├── features/                   # Self-contained feature modules
│   ├── gateway/               # Python MCP Gateway code
│   ├── cipher/                # Cipher Memory service
│   ├── n8n/                   # Workflow automation
│   ├── yt/                    # YouTube Mini Agent
│   └── ...                    # Other feature packs
├── scripts/                    # Management scripts (Start, Stop, Status)
└── docs/                       # Documentation
    └── archive/               # Legacy reference docs
```

## 3. Core Services
The system is orchestrated by `core/docker-compose/base.yml`. Key services include:

| Service | Container Name | Port | Role |
| :--- | :--- | :--- | :--- |
| **MCP Gateway** | `mcp-gateway` | `2091` | Primary entrypoint. Routes requests to agents/tools. |
| **TensorZero** | `tensorzero` | `3000` | LLM Gateway. Unified API for OpenAI, Ollama, etc. |
| **Agent Zero** | `agent-zero` | `8080` | (Optional) Full agentic framework. |
| **n8n Agent** | `pmz-n8n` | `5678` | Workflow automation agent. |
| **Cipher Memory** | `pmz-cipher` | `8081` | Shared memory/state for agents. |
| **YT Mini** | `pmz-yt-mini` | N/A | Lightweight background YouTube processor. |

## 4. Networking
All services share a single bridge network: `pmoves_ai`.
*   **Service Discovery:** Services talk to each other by container name (e.g., `http://tensorzero:3000`).
*   **External Access:**
    *   `mcp-gateway` exposed on `2091`.
    *   `tensorzero` exposed on `3000`.
    *   `n8n` exposed on `5678`.

## 5. Configuration
*   **Environment:** Centralized in `.env`.
*   **MCP Tools:** Defined in `core/mcp/catalog.yml`.
*   **Models:** Configured in `config/tensorzero.toml`.

## 6. Development Workflow
1.  **Start:** `./scripts/start_pmoves.ps1` (Windows) or `sh` equivalent.
2.  **Status:** `./scripts/pmoves_status.ps1`.
3.  **Logs:** `docker logs -f <container_name>`.

## 7. Relationship to "Reference Architecture"
*   **Legacy Docs:** `docs/archive/PMOVES.AI_Reference` contains the full Enterprise docs.
*   **BoTZ Difference:** BoTZ is a subset. We do *not* currently deploy the 5-Tier network, SupaSerch, or DeepResearch by default, opting for a simpler, faster local stack.
