# PMOVES-BoTZ

PMOVES-BoTZ is the unified, self-hosted PMOVES stack. It replaces the older pack-based layout (`pmoves_multi_agent_pack`, `pmoves_multi_agent_pro_pack`, `pmoves_multi_agent_pro_plus_pack`, `pmoves-mini-agent-box`) with a single coherent application built from a `core/` + `features/` architecture.

## Requirements

- Docker and Docker Compose
- Python 3.11+
- Node.js 20+ and pnpm (for Cipher memory integration)

## New Features

### Cipher Memory Integration

PMOVES-BoTZ now includes advanced memory capabilities through Pmoves-cipher integration:

- **Persistent Knowledge Storage**: Store and retrieve coding patterns, solutions, and insights across sessions
- **Reasoning Pattern Preservation**: Capture and reuse decision-making processes and problem-solving approaches
- **Cross-Session Learning**: Agents improve over time through accumulated experience
- **Memory-Enhanced Modes**: Auto-research and code-runner modes now leverage persistent memory
- **Advanced Workflow Templates**: Memory-driven workflows for complex multi-agent coordination

## Quick Start (Self-Hosted)

1. **Environment**
   - Copy `.env` from the provided example (if present) and set required keys (OpenAI, GEMINI, E2B, etc.).
2. **Start the stack**
   - PowerShell: `./scripts/bring_up_pmoves_botz.ps1`
   - Bash: `./scripts/bring_up_pmoves_botz.sh`
3. **Status & metrics**
   - Run `./scripts/pmoves_status.(ps1|sh)` to check service health.
   - Prometheus: `http://localhost:${PROMETHEUS_PORT:-9090}/targets`
   - Grafana: `http://localhost:${GRAFANA_PORT:-3033}`
4. **Cipher UI & API**
   - UI: `http://localhost:3010`
   - API: `http://localhost:3011`
   ```bash
   cd pmoves_multi_agent_pro_pack/memory_shim
   ./setup_cipher.sh  # Linux/macOS
   # or
   .\setup_cipher.ps1  # Windows
   ```

3. **Configure Environment**
   ```bash
   export OPENAI_API_KEY=sk-your-key
   ```

4. **Deploy with Memory**
   ```bash
   # Recommended: unified overlays (works cross‑platform)
   export PMZ_NAMESPACE=botz-dev
   export COMPOSE_PROJECT_NAME=$PMZ_NAMESPACE
   docker compose --env-file .env -f core/docker-compose/base.yml -f features/pro/docker-compose.yml up -d
   ```

   Notes:
   - On Linux, to enable Tailscale HTTPS exposure, add the `linux` profile:
     `COMPOSE_PROFILES=linux docker compose -f core/docker-compose/base.yml -f features/pro/docker-compose.yml up -d`
   - Cipher Memory runs on ports 3010 (UI) and 3011 (API) when enabled via Pro pack compose.
   - Prefer the new PMOVES-BotZ gateway proxy by adding `-f features/gateway-proxy/docker-compose.yml` to the compose command.

For detailed setup instructions, see [Cipher Memory Integration Guide](docs/CIPHER_MEMORY_INTEGRATION.md).

## Mini-Agent CLI (Experimental)

PMOVES-BoTZ includes an experimental CLI that treats core services as a small team of “mini agents” and provides helpers for exploration and health checks.

- Run interactively:
  ```bash
  python scripts/pmoves_cli.py
  ```
  Commands include:
  - `status` – shows stack status using the existing `pmoves_status` script.
  - `agents` – lists known mini agents (gateway, docling, cipher, VL-sentinel, Crush, planned yt-mini).
  - `agent <name>` – shows details and health for a specific agent.
  - `docs <query>` – searches `docs/` for matching filenames.
   - `llm` – shows detected LLM backend options (local Ollama, Cipher cloud, future TensorZero).

- Run a single command:
  ```bash
  python scripts/pmoves_cli.py list-agents
  python scripts/pmoves_cli.py agent cipher
   python scripts/pmoves_cli.py llm-options
  ```
