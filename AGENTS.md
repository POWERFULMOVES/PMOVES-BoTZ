PMOVES-BoTZ • Agents Guide (AGENTS.md)

Purpose
- This file gives human/AI agents concrete rules-of-the-road for working in this repo: how the stack is organized, how to run it self-hosted, how to make changes safely, and what to verify before merging.
- Scope: applies to the entire repository. If a directory introduces a more specific AGENTS.md, the deeper file takes precedence for files within that subtree.

Refactor Context (PMOVES-BoTZ from PMOVES-Kilobots)
- This repository originated as PMOVES-Kilobots with multiple "pack" variants; it is being unified into a single application named PMOVES-BoTZ, following the plan in `PMOVES_Edition.md` and `GEMINI.md`.
- The target canonical layout is:
  - `core/` for shared infrastructure (compose, MCP, core configs).
  - `features/` for modular capabilities (cipher, e2b, metrics, slack, discord, vl_sentinel, n8n, etc.).
  - `scripts/`, `docs/`, and `tests/` for unified scripts, documentation, and testing.
- Legacy pack directories (`pmoves_multi_agent_pack`, `pmoves_multi_agent_pro_pack`, `pmoves_multi_agent_pro_plus_pack`, `pmoves-mini-agent-box`) are legacy and should be treated as read-only reference. Do not add new code, configs, or docs to these packs.
- All new work (compose, MCP catalogs/modes, features, scripts, docs) should land in `core/`, `features/`, `scripts/`, `docs/`, or `tests/`—never as new "pack" variants.

Features_folder Staging Area
- The former `Features_folder/` staging area has been moved under `archive/Features_folder/` and is no longer part of the live stack.
- All enhancements from `Features_folder/` have been folded into the canonical `features/` and `core/` locations; treat the archived copy as read-only historical reference.
- Do not wire services or scripts to paths under `archive/Features_folder/`; use `features/` instead.
- New enhancements should go straight into `features/` rather than recreating a new staging folder.

AI Agent Coordination (GEMINI.md)
- `GEMINI.md` captures AI-agent-specific instructions for continuing the PMOVES-BoTZ refactor (single source of truth, modular features, unified scripts).
- Keep `AGENTS.md` as the ground-truth operational guide for humans/agents; if you materially change the refactor plan, directory layout, or workflows, update both `AGENTS.md` and `GEMINI.md` to stay in sync.
- Follow the "single source of truth" principle from `GEMINI.md`: avoid duplicate compose/MCP/script definitions; consolidate into `core/` and `features/` instead of copying.

High-Level Architecture (Self-Hosted)
- Services (compose-based):
  - mcp-gateway (HTTP MCP gateway)
  - docling-mcp (document processing MCP server)
  - e2b-runner (sandbox runner; uses E2B_API_KEY)
  - vl-sentinel (vision-language sentinel; defaults to host Ollama)
  - cipher-memory (PMoves‑Cipher UI/API)
  - Metrics: Prometheus + Grafana + Alertmanager (+ host prom/blackbox exporter)
- Networks and discovery:
  - Internal DNS via compose networks; service labels `pmoves.service` and `pmoves.health` enable label‑based autodiscovery.
  - Autodiscovery script writes Prometheus file_sd targets and local MCP client config.

Runbook (Repo Root)
- Environment:
  - Use root `.env`. Bring-up scripts auto‑bootstrap it from examples if missing.
  - Do not commit secrets. `.env` is dev‑local and excluded from VCS.
- Start:
  - PowerShell: `./scripts/bring_up_pmoves_botz.ps1`
  - Bash: `./scripts/bring_up_pmoves_botz.sh`
  - Optional port modes: set `PMZ_INTERNAL_ONLY=1` (no host ports) or `PMZ_EPHEMERAL=1` (random host ports) before running.
- Status & health:
  - `./scripts/pmoves_status.ps1` or `./scripts/pmoves_status.sh`
  - Prometheus: `http://localhost:${PROMETHEUS_PORT:-9090}/targets`
  - Grafana: `http://localhost:${GRAFANA_PORT:-3033}` (dashboards: PMOVES Overview, PMOVES Services Health)
- Autodiscovery:
  - `python ./scripts/prom_autodiscover.py`
  - Writes `features/metrics/file_sd/blackbox_targets.yml` and `config/codex/local_mcp.json`.
  - Avoids duplicates by skipping statically-declared targets in `features/metrics/prometheus.yml`.

PMoves‑Cipher (UI/API)
- UI: `http://localhost:3010`  •  API: `http://localhost:3011` (via `features/cipher/docker-compose.yml`).
- Defaults for self‑hosted:
  - OAuth2 disabled by default (`OAUTH2_ENABLED=false` in compose). Provide credentials to enable.
  - An encryption key is provided for dev (`CIPHER_ENCRYPTION_KEY`); replace in non‑dev.
- Implementation notes for agents:
  - UI start requires a `.env` the app expects under `dist/`; the image and entry logic ensure it exists.
  - Agent config path passed as `--agent memAgent/cipher_pmoves.yml`.

VL‑Sentinel (Vision‑Language)
- Defaults to host Ollama: `OLLAMA_BASE_URL=http://host.docker.internal:11434`.
- For healthy status, run Ollama and pull a model, e.g. `qwen2.5-vl:14b`.

E2B Runner
- Uses `E2B_API_KEY` from root `.env` to report healthy.

Metrics & Blackbox
- Prometheus/Alertmanager/Grafana compose overlay is under `features/metrics/`.
- Blackbox exporter is expected on host at `:9115` (replaceable). Prometheus’s `blackbox` job targets are static+file_sd; autodiscovery only writes non‑static extras.

Compose & Overlays
- Base: `core/docker-compose/base.yml`
- Overlays: `features/pro`, `features/cipher`, `features/metrics`, `features/network/{external,internal,ephemeral}.yml`
- Windows bring‑up supports the same overlays as Bash.

Kilo‑Bots Theme (for UX/Docs)
- The “mini transformers team” consists of Gateway, Docling, VL, Cipher, Runner.
- Keep wording “self‑hosted”; prefer neutral, developer‑centric language in code and commit messages; theme is for docs/UX.

Contribution Rules (Agents)
- Make minimal, surgical diffs. Do not rename large directories or "packs" casually. If a rename/refactor is needed, propose a short plan first.
- Respect existing structure:
  - Keep bring-up parity across PowerShell and Bash.
  - Update docs when behavior/flags change.
  - Preserve autodiscovery contract (labels, file_sd path, MCP config path).
- Single source of truth for infra:
  - Docker Compose: use `core/docker-compose/base.yml` and overlays as the canonical definitions; do not recreate pack-specific compose files.
  - MCP configuration: use `core/mcp/catalog.yml` and `core/mcp/modes/` as the only authoritative MCP catalog/mode locations.
  - Features: treat `features/` as the canonical home for all feature code; fold in improvements from `Features_folder/` rather than forking behavior.
- Secrets:
  - Never commit real keys or tokens. Use `.env` locally; scrub logs in docs.
- Commit messages:
  - Conventional prefixes: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `perf:`.
  - Examples used in this repo: `feat(startup,docs): …`, `fix(autodiscover): …`, `feat(cipher-ui,local-first): …` (use “self‑hosted” going forward).
- Coding style/tooling:
  - Python 3.11+, Node 20+, Docker Compose v2.
  - Prefer cross‑platform scripts; keep PS1 and SH behavior aligned.
  - Avoid breaking line endings; repo mixes LF/CRLF—do not mass‑convert.
- Tests/validation before merge:
  - Start stack; confirm Gateway and Docling are UP and healthy.
  - Run `python ./scripts/prom_autodiscover.py`; verify Prometheus targets have no duplicated blackbox items.
  - Open Grafana dashboards; confirm panels populate.
  - If touching Cipher, confirm UI reachable on 3010 and API on 3011.

When to Add New Overlays or Features
- Prefer adding a `features/<name>/docker-compose.yml` overlay rather than modifying base.
- For automation (e.g., n8n), add an optional overlay and import workflows from `workflows/n8n/`.

MCP Clients & Local Mapping
- `scripts/prom_autodiscover.py` writes `config/codex/local_mcp.json` mapping to resolved gateway host port and optional Cipher API.
- If you change gateway or cipher ports, ensure the script still resolves them via env or `docker inspect`.

Safety & Rollback
- If a service is failing, bring it up individually with compose to inspect logs.
- Favor “disable by default” for optional subsystems (OAuth2, external providers) in self‑hosted dev.

Contact Points / Typical Tasks (Quicklinks)
- Start stack: `./scripts/bring_up_pmoves_botz.(ps1|sh)`
- Status: `./scripts/pmoves_status.(ps1|sh)`
- Autodiscovery: `python ./scripts/prom_autodiscover.py`
- Prometheus targets: `http://localhost:${PROMETHEUS_PORT}/targets`
- Cipher UI: `http://localhost:3010`

Change Control
- Any change to service ports, health endpoints, label keys, or paths must update:
  - compose overlays (port exposure/health)
  - autodiscovery (label reading / file paths)
  - docs (Quick Start / Self‑Hosted guide)

Tailscale (Self‑Hosted Access)
- Where: `core/docker-compose/base.yml` includes a `tailscale` service (linux profile) that:
  - runs `tailscaled`, authenticates with `TS_AUTHKEY`, and serves HTTPS via `tailscale serve https / http://127.0.0.1:2091`.
  - persists state in `core/ts-state/`.
- OS support:
  - Linux only (requires `CAP_NET_ADMIN`, `NET_RAW`, and host networking). It’s behind the `linux` profile; not started by default on Windows/macOS.
- Enable (Linux):
  - Set `TS_AUTHKEY` in root `.env` (or env var).
  - Start with profile: `docker compose --env-file .env -f core/docker-compose/base.yml --profile linux up -d tailscale`.
  - Ensure gateway is reachable on host `:2091` so Tailscale can proxy it.
- Security:
  - Treat `TS_AUTHKEY` as secret. Do not commit.
  - `tailscale serve` exposes the gateway over your tailnet; validate ACLs and turn off if not required.
  - Clear `core/ts-state/` if rotating identity.
