# PMOVES-BoTZ

PMOVES-BoTZ is a unified multi-agent platform for document processing, memory management, API testing, sandbox execution, and vision-language processing.

## Structure

- `core/`: Core infrastructure and configurations.
  - `docker-compose/`: Docker Compose files.
  - `mcp/`: MCP server catalog and modes.
- `features/`: Feature-specific code and configurations.
  - `cipher/`: Cipher Memory.
  - `docling/`: Docling Document Processing.
  - `e2b/`: E2B Sandbox Runner.
  - `vl_sentinel/`: Vision-Language Sentinel.
  - `gateway/`: MCP Gateway.
- `scripts/`: Unified management scripts.
  - `start.ps1`: Start the application.
  - `stop.ps1`: Stop the application.
  - `test.ps1`: Run tests.
  - `setup.ps1`: Initial setup.
- `tests/`: Integration tests.

## Quick Start

1.  **Setup**:
    ```powershell
    .\scripts\setup.ps1
    ```

2.  **Start**:
    ```powershell
    .\scripts\start.ps1
    ```

3.  **Stop**:
    ```powershell
    .\scripts\stop.ps1
    ```

## Services

- **MCP Gateway**: http://localhost:2091
- **Docling MCP**: http://localhost:3020
- **E2B Runner**: http://localhost:7071
- **VL Sentinel**: http://localhost:7072
- **Cipher Memory**: http://localhost:8081 (STDIO/HTTP)
- **YT Mini Agent**: CLI/Service (Optional)

## Documentation

See `docs/` for detailed documentation.
