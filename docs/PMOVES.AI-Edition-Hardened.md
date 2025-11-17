PMOVES.AI Edition — Hardened Integrations, Images, and CI/CD

Overview
- Goal: treat each external integration as a first‑class, hardened submodule with a pinned image in GHCR, reproducible builds, and CI parity with PMOVES.AI.
- Scope: Archon, Agent Zero, PMOVES.YT, Channel Monitor, Invidious stack, Jellyfin bridge/AI overlay, Notebook/Surreal, DeepResearch, SupaSerch, TensorZero, and core data services (Qdrant, Meili, Neo4j, MinIO, Supabase REST/PostgREST).
- Deliverables: submodule layout, image catalog, hardening baseline, MCP catalog notes, migration plan, and verification gates.

Inventory (as of Nov 11, 2025)
- Local‑build services (compose `build:`):
  - `services/archon` (API/UI), `services/agent-zero`, `services/channel-monitor`, `services/jellyfin-bridge`, `services/deepresearch`, `services/supaserch`, `services/hi-rag-gateway(-v2)(-gpu)`, `services/invidious-companion-proxy`, `services/grayjay-plugin-host`, `services/presign`, `services/render-webhook`, `services/extract-worker`, `services/notebook-sync`, `services/media-*`, `services/retrieval-eval`, `services/mesh-agent`.
- Pulled images (compose `image:`):
  - Datastores: `ankane/pgvector`, `neo4j:5.22`, `qdrant/qdrant:v1.10.0`, `getmeili/meilisearch:v1.8`, `minio/minio:latest`.
  - Supabase REST: `postgrest/postgrest:latest` (+ CLI variant).
  - Messaging/infra/monitoring: `nats:2.10-alpine`, `prom/*`, `grafana/*`, `loki`, `promtail`, `cadvisor`.
  - Media/YT: `quay.io/invidious/*:latest`, `postgres:14` (Invidious DB), `brainicism/bgutil-ytdlp-pot-provider:1.2.2`.
  - TensorZero stack: `clickhouse/clickhouse-server:24.12-alpine`, `tensorzero/gateway`, `tensorzero/ui`.
  - Ollama sidecar: `${PMOVES_OLLAMA_IMAGE:-pmoves/ollama:0.12.6}`.
  - Optional externals: `ghcr.io/.../pmoves-health-wger:pmoves-latest`, `ghcr.io/.../pmoves-firefly-iii:pmoves-latest`.

Immediate Stabilization — Archon
- Status: DNS flaps with Supabase CLI stack caused startup failures. Compose now injects `SUPA_REST_URL=http://postgrest:3000` into the `archon` container to remove host DNS dependency.
- Proposed follow‑ups:
  - Env fallbacks inside Archon: accept any of `SUPA_REST_URL`, `SUPABASE_REST_URL`, or (`SUPABASE_URL` + `SUPABASE_ANON_KEY`). Precedence: explicit REST URL > Supabase URL pair.
  - Health probe: block readiness until REST HEAD/GET 200 on `/` and `/healthz` with exponential backoff; surface last error in `/healthz` body.
  - Compose: set `depends_on` + `healthcheck` against `postgrest` service to reduce flapping during parallel bring‑up.
  - CI check: add `make -C pmoves archon-smoke` to hit `/healthz` and a trivial REST query via the injected anon key or service role.
  - Implemented: container `healthcheck` for Archon (`/healthz` validates Supabase reachability) and `/ready` endpoint; `make archon-smoke` checks `/healthz` and PostgREST root on `:3010`.

Submodule Strategy (Integrations as Repos)
- Rationale: separate upstream integration code from PMOVES.AI customization; enable independent CI, issue tracking, and GHCR publishing; reduce diff noise in this monorepo.
- Target submodules (new repos under the organization):
  - `PMOVES.YT`, `PMOVES.Archon`, `PMOVES.AgentZero`, `PMOVES.ChannelMonitor`, `PMOVES.JellyfinBridge`, `PMOVES.DeepResearch`, `PMOVES.SupaSerch`, `PMOVES.HiRAG.Gateway`, `PMOVES.GrayjayProxy`.
- Branching/namespacing:
  - Each integration maintains `main` mirroring upstream and a `pmoves/edition` branch carrying our overlays (config, small patches, default envs, health endpoints).
  - Policy: upstream PR first where viable; otherwise, keep overlay minimal and documented.
- Migration steps:
  1) Extract `pmoves/services/<integration>` into its repo preserving history (`git subtree split`), create `pmoves/edition` branch.
  2) Re‑introduce here as `git submodule` under `pmoves/integrations/<name>`.
  3) Update compose to prefer `image: ghcr.io/<org>/<name>:pmoves-latest`; keep `build:` path behind a `profile: [dev-local]` toggle.
  4) Add release workflow: build, SBOM, sign, push, publish provenance; update `pmoves/env.shared` image pin variables.

Hardened Image Catalog (Baseline Controls)
- Supply chain
  - Reproducible builds: pinned tags + digests; prefer distroless/alpine where appropriate.
  - SBOM: generate CycloneDX + SPDX; store as build artifact and attach to GHCR images.
  - Signing: Cosign keyless; verify in `make verify-all` using `cosign verify --certificate-oidc-issuer` policy.
  - Vulnerability scan: Trivy/Grype in CI; block on HIGH/CRITICAL with allowlist only for false positives.
- Runtime security (compose defaults per service)
  - Run as non‑root; read‑only root FS; `no-new-privileges: true`.
  - Linux hardening: drop all capabilities; add back only needed (`CAP_NET_BIND_SERVICE` for <1024 if applicable).
  - Seccomp/AppArmor: apply default Docker profiles; document exceptions.
  - Network: explicit `networks:` sections; disable inter‑service connectivity by default; egress allowlist for known APIs.
  - Resource limits: CPU/mem limits per service; healthchecks with backoff; restart policies `unless-stopped`.
  - Secrets: mount via env files or Docker secrets; avoid composing long secrets inline; rotate via `make supabase-boot-user` and CHIT bundles.
- Observability
  - Uniform `/healthz` and optional `/ready` endpoints; Prometheus metrics where available; Loki labels standardized.
  - Evidence capture: extend `make verify-all` to attach key logs and health JSON into `pmoves/docs/SESSION_IMPLEMENTATION_PLAN.md`.

Dynamic MCP Catalog (Docker‑backed Tools)
- Maintain a registry of Dockerized agent tools (MCP servers) used by integrations; map tool → image → version → ports → scopes.
- Add a generator script to emit a machine‑readable catalog (JSON) from compose + submodules, consumed by MCP clients.
- Security: run tools behind a local gateway with auth; use per‑tool networks; opt‑in exposure via profiles.

CI/CD Plan
- Per‑integration (in submodule repos): build → test → scan → SBOM → sign → push to GHCR; publish `:pmoves-latest` and immutable `:YYYYMMDD.sha` tags.
- Monorepo verification: `make verify-all` pulls pinned digests and runs smokes (`core`, `gpu`, `monitoring`, externals), failing fast on image provenance or healthcheck.
- Renovate: automate tag/digest bumps with PRs, gated by smokes.
 - Implemented: integrations GHCR workflow now emits SBOM (CycloneDX via Syft), runs Trivy (HIGH/CRITICAL gating), and Cosign‑signs all published tags (keyless).

Migration Checklist
- Extract services into submodules (priority: PMOVES.YT, Archon, Agent Zero, Channel Monitor).
- Update compose to image‑first flow with `profiles: [integrations]` and dev‑local build toggles. Archon now prefers submodule build by default in local bring‑up; use published‑images targets to override.
- Add override `pmoves/docker-compose.integrations.images.yml` and `make up-yt-published` to run PMOVES.YT from GHCR without local builds.
- Add security defaults to compose templates (`security_opt`, `read_only`, `cap_drop`, `user`, `healthcheck`).
 - Implemented: `pmoves/docker-compose.hardened.yml` adds non‑root, read‑only, tmpfs /tmp, cap_drop, and no‑new‑privileges for Archon, PMOVES.YT, and Channel Monitor. Use `make up-agents-hardened` and `make up-yt-hardened`.
- Pin images in `pmoves/env.shared`; document overrides.
- Wire CI for GHCR, Cosign, Trivy; add status badges to each repo README.

Verification Gates
- Local-first (Ollama-only) pass:
  - Bring up the unified PMOVES-BoTZ stack with `./scripts/bring_up_pmoves_botz.(ps1|sh)` (no external API keys required).
  - Run `python scripts/smoke_tests.py` to validate:
    - Compose stacks (`core/` + `features/metrics` + `features/network/*`).
    - Core BoTZ services: gateway (`/health` on MCP_GATEWAY_PORT) and Docling (`/health` on DOCLING_MCP_PORT).
    - VL-Sentinel: `/health` on `VL_PORT` (default 7072) using the configured Ollama VL model (e.g. `qwen2.5-vl:14b` on the RTX 5090 host).
    - Cipher memory:
      - Static: `features/cipher/pmoves_cipher` present, build artifacts in `dist/`, memAgent config.
      - Runtime: Cipher API/UI responding on `CIPHER_API_PORT`/`CIPHER_UI_PORT` (defaults 3011/3010).
    - Metrics: Prometheus `/targets` and Grafana `/login` on the configured ports.
    - External APIs (Postman, Tailscale) are treated as optional; missing keys log a skip but do not fail the local pass.
- Cloud-augmented (LLM + externals) pass:
  - Provide hardened `VENICE_API_KEY` / `OPENAI_API_KEY`, Postman, and Tailscale keys via `.env` or secret bindings.
  - Re-run `python scripts/smoke_tests.py` and ensure:
    - Cipher LLM key checks pass (Venice/OpenAI format validation).
    - Postman and Tailscale connectivity checks return HTTP 200 / valid auth formats.
  - `make -C pmoves verify-all`:
    - Confirms image signatures and SBOM presence for all integrations.
    - Asserts `/healthz` 200 for Archon, Agent Zero, Channel Monitor, Jellyfin bridge, Hi-RAG gateways (CPU/GPU) and Invidious endpoints.
    - Ensures Supabase REST reachability from Archon using `SUPA_REST_URL` fallback.

Open Items / Decisions
- Confirm whether Archon vendor expects `SUPABASE_URL`/`ANON_KEY`. If yes, add those as secondary fallbacks and document precedence.
- Define minimal capability sets per service (TBD per container analysis).
- Establish MCP catalog schema and generation path.

References
- Compose: `pmoves/docker-compose.yml` and `pmoves/compose/*.yml`.
- Local CI: `docs/LOCAL_CI_CHECKS.md`.
- Smokes and runbooks: `pmoves/docs/SMOKETESTS.md`, `pmoves/docs/LOCAL_DEV.md`.
