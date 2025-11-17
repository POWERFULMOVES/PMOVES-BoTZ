# PMOVES-BoTZ Refactoring Plan: "PMOVES Edition"

This document outlines the plan to refactor the `PMOVES-Kilobots` repository into a unified, single application called `PMOVES-BoTZ`.

## 1. Goal

The primary goal is to eliminate the complexity and redundancy of the current "pack" system (`mini`, `multi-agent`, `pro`, `pro-plus`) and create a single, coherent application with a clear, modular structure.

## 2. Proposed Directory Structure

All features will be consolidated under the `features` and `core` directories. The top-level pack directories will be removed.

```
C:\Users\russe\Documents\GitHub\PMOVES-Kilobots\
├── core/
│   ├── docker-compose/
│   │   ├── base.yml         # Core services (gateway, docling)
│   │   └── overlays/        # Overlays for different envs
│   │       ├── development.yml
│   │       ├── production.yml
│   │       └── testing.yml
│   ├── mcp/
│   │   ├── modes/           # Unified MCP modes
│   │   └── catalog.yml      # Unified MCP catalog
│   └── ...
├── features/
│   ├── cipher/            # Cipher-memory feature
│   ├── e2b/               # E2B sandbox feature
│   ├── metrics/           # Prometheus/Grafana metrics
│   ├── postman/           # Postman integration
│   ├── slack/             # Slack integration
│   ├── discord/           # Discord integration
│   ├── vl_sentinel/       # VL-Sentinel feature
│   └── n8n/               # n8n workflows
├── scripts/               # Unified scripts
├── docs/                  # Unified documentation
├── tests/                 # All tests
├── .gitignore
├── README.md              # Updated README
├── AGENTS.md              # Updated AGENTS.md
└── GEMINI.md              # New file for AI agent context
```

## 3. Refactoring Steps

### Step 1: Consolidate Docker Compose Files (Completed)

1.  **Create a base `docker-compose.yml`:** A new `core/docker-compose/base.yml` was created. It contains all the services from all the packs.
2.  **Use overlays for environment-specific configurations:** `development.yml` and `production.yml` were created in `core/docker-compose/overlays/`.
3.  **Remove old `docker-compose` files:** All the `docker-compose.*.yml` files from the pack directories were deleted.

### Step 2: Unify MCP Configuration (Completed)

1.  **Create a single `catalog.yml`:** All `mcp_catalog_*.yaml` and `mcp_mini_portable.yaml` files were merged into a single `core/mcp/catalog.yml`.
2.  **Consolidate modes:** All unique modes from the pack directories were moved to `core/mcp/modes/`.

### Step 3: Reorganize Feature Directories (Completed)

1.  **Move feature code:** The code for each feature was moved from the pack directories into the corresponding `features/` subdirectory. For example:
    *   `pmoves_multi_agent_pro_pack/memory_shim` -> `features/cipher/`
    *   `pmoves_multi_agent_pro_pack/e2b_shim` -> `features/e2b/`
    *   `pmoves_multi_agent_pro_pack/metrics` -> `features/metrics/`
    *   `pmoves-mini-agent-box/discord_bot` -> `features/discord/`
    *   `pmoves_multi_agent_pro_pack/vl_sentinel` -> `features/vl_sentinel/`
    *   `pmoves_multi_agent_pro_pack/workflows/n8n` -> `features/n8n/`
    *   `pmoves-mini-agent-box/crush_shim` -> `features/crush/`
2.  **Move n8n workflows:** `workflows/n8n/docling_postman_vl.json` was moved to `features/n8n/workflows/`.
3.  **Archive staging folder:** The temporary `Features_folder/` staging directory was moved under `archive/Features_folder/` after its contents were folded into `features/`. It is retained only as historical reference and is not part of the live stack.

### Step 4: Unify Scripts

1.  **Consolidate scripts:** Merge all the run scripts (`run_*.sh`, `run_*.ps1`), setup scripts, and test scripts into a single set of scripts in the `scripts/` directory.
2.  **Update scripts:** The scripts will need to be updated to use the new `docker-compose` structure with overlays.

### Step 5: Update Documentation

1.  **Update `README.md`:** Rewrite the main `README.md` to provide a clear overview of the unified `PMOVES-BoTZ` application, how to run it, and how to use its features.
2.  **Update `AGENTS.md`:** Update `AGENTS.md` to reflect the new directory structure, configuration, and contribution guidelines.
3.  **Remove old `README` files:** Delete all the `README` files from the pack directories.

### Step 6: Create `GEMINI.md`

Create a new `GEMINI.md` file at the root of the repository. This file will contain:
*   A summary of the refactoring plan.
*   Instructions for an AI agent on how to perform the refactoring steps.
*   Key architectural decisions and conventions to follow.

## 4. Validation

After the refactoring, the following should be true:

1.  The application can be started with a single `docker-compose` command (using the appropriate overlays).
2.  All features from all the packs are available and functional in the unified application.
3.  All tests pass.
4.  The documentation is accurate and up-to-date.

## 5. PMOVES-BoTZ as a Team of Mini Agents

PMOVES-BoTZ should be understood as a **layered team of mini agents**, rather than a single monolithic service:

- **CLI Mini Agents (feature layer)**
  - Each major feature (Cipher, Docling, VL-Sentinel, future YT mini, etc.) has:
    - A local CLI / process entrypoint that can bootstrap the service it is responsible for.
    - Access to MCP tools and other stack services.
    - A **provider-native** implementation that leverages that provider's SDKs/APIs directly (e.g., Cipher’s Node/HTTP APIs, YT’s media tooling, Archon’s cloud runners).
  - These CLIs are the "mini agents" of the team, focused on a specific domain (documents, memory, media, etc.).
  - Once all core services are green, the first mission of the CLI layer is to **self-catalog**:
    - Identify and describe each mini agent and its tools.
    - Capture Cipher’s MCP/A2A metadata (e.g., `/.well-known/agent.json`) and other agent descriptors.
    - Feed this catalog into the documentation/knowledge layer (PMOVES-DoX and related repos).

- **Service Layer (containers / overlays)**
  - CLI mini agents are packaged as Docker services under `core/` + `features/` and can be composed via overlays.
  - Example: `features/cipher` exposes a CLI-driven memory agent that also runs as the `cipher-memory` service.
  - Optional features (metrics, YT mini, etc.) are modeled as overlays (e.g., `features/metrics`, future `features/yt`).

- **Gateway & Big-Bro Agents (orchestration layer)**
  - The MCP gateway and higher-level orchestrator modes act as "big bro" agents:
    - They call into the mini agents via MCP, HTTP, or CLI invocations.
    - They coordinate workflows across multiple mini agents (Docling + Cipher + VL-Sentinel, etc.).

This layered model keeps each feature self-contained (with its own provider-native CLI and tests) while allowing PMOVES-BoTZ to operate as a coordinated team of agents through the gateway and MCP modes, and to publish a unified catalog of agents/tools into PMOVES-DoX.

- **Local LLM Orchestration (Crush + Ollama)**
  - For local models, PMOVES-BoTZ prefers a **Crush + Ollama** path:
    - Ollama provides local model execution.
    - Crush acts as a local LLM router/orchestrator that can be customized to present itself as “PMOVES-BoTZ” while calling into Ollama.
  - This allows provider-native agents to fully leverage their SDKs/APIs, while keeping a consistent PMOVES-BoTZ identity at the CLI/agent layer.
