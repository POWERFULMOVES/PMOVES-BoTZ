# Docker Compose Configuration Strategy

## Core Base Configuration (`core/docker-compose/base.yml`)
Contains services common to all configurations:

```yaml
version: '3.9'

x-common-env: &common_env
  - TS_AUTHKEY=${TS_AUTHKEY}
  - TS_STATE_DIR=/var/lib/tailscale

services:
  tailscale:
    image: tailscale/tailscale:stable
    hostname: pmoves-core
    environment: *common_env
    cap_add: [ "NET_ADMIN", "NET_RAW" ]
    volumes:
      - ./core/ts-state:/var/lib/tailscale
    network_mode: host
    restart: unless-stopped
    command: >
      sh -lc "
      tailscaled --state=/var/lib/tailscale/tailscaled.state &
      sleep 2 &&
      tailscale up --authkey=${TS_AUTHKEY} --reset --accept-routes=true --ssh=true &&
      tailscale serve https / http://127.0.0.1:2091 &&
      tail -f /dev/null
      "

  mcp-gateway:
    image: alpine:3.20
    working_dir: /app
    environment:
      - POSTMAN_API_KEY=${POSTMAN_API_KEY}
    volumes:
      - ./core/mcp_catalog.yaml:/app/mcp_catalog.yaml:ro
    network_mode: host
    restart: unless-stopped
    command: >
      "
      apk add --no-cache bash curl python3 py3-pip pipx docker-cli-plugins &&
      pipx ensurepath &&
      docker mcp gateway run --port 2091 --transport streaming --catalog /app/mcp_catalog.yaml
      "
```

## Feature-Specific Overrides

### Pro Features (`features/pro/docker-compose.yml`)
Adds E2B sandbox and Vision-Language components:

```yaml
version: '3.9'

services:
  e2b-runner:
    build: ./features/pro/e2b_shim
    environment:
      E2B_API_KEY: ${E2B_API_KEY}
      SANDBOX_TTL_SEC: ${SANDBOX_TTL_SEC:-1800}
    ports: [ "7071:7071" ]

  vl-sentinel:
    build: ./features/pro/vl_sentinel
    environment:
      VL_PROVIDER: ${VL_PROVIDER:-ollama}
      VL_MODEL: ${VL_MODEL:-qwen2.5-vl:14b}
      OLLAMA_BASE_URL: ${OLLAMA_BASE_URL:-http://host.docker.internal:11434}
```

### Mini Configuration (`features/mini/docker-compose.yml`)
Lightweight profile with simplified catalog:

```yaml
version: '3.9'

services:
  mcp-gateway:
    volumes:
      - ./features/mini/mcp_mini_portable.yaml:/app/mcp_catalog.yaml:ro
```

### Pro-Plus Additions (`features/pro-plus/docker-compose.yml`)
Local Postman integration:

```yaml
version: '3.9'

services:
  postman-mcp-local:
    image: node:20-alpine
    environment:
      POSTMAN_API_KEY: ${POSTMAN_API_KEY}
    command: ["npx", "@postman/postman-mcp-server@latest", "--full"]
    network_mode: host
```

## Composition Workflow
1. **Basic Configuration** (Core + Docling):
   ```bash
   docker compose -f core/docker-compose/base.yml -f features/basic/docker-compose.yml up
   ```

2. **Pro Configuration** (Basic + E2B/VL):
   ```bash
   docker compose -f core/docker-compose/base.yml -f features/basic/docker-compose.yml -f features/pro/docker-compose.yml up
   ```

3. **Mini Configuration** (Core only):
   ```bash
   docker compose -f core/docker-compose/base.yml -f features/mini/docker-compose.yml up
   ```

## Key Implementation Notes
- All feature profiles **MUST** maintain compatibility with base service names
- Environment variables follow hierarchy: `core/.env` → `features/*/env` → local `.env`
- Service ports are pre-allocated to prevent conflicts:
  - 7071: E2B Runner
  - 7072: VL Sentinel
  - 3020: Docling MCP