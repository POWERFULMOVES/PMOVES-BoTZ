# Cipher Memory Port Configuration Change

## Issue
Cipher Memory service was configured to use port 8080, which conflicts with another service using the same port.

## Solution
Changed Cipher Memory to use port 8081 and made it configurable via environment variable.

## Changes Made

### 1. docker-compose.mcp-pro.yml
- Changed port mapping from `"8080:8080"` to `"${CIPHER_MEMORY_PORT:-8081}:8081"`
- Added environment variable `CIPHER_MEMORY_PORT: ${CIPHER_MEMORY_PORT:-8081}`
- Updated health check to use port 8081

### 2. memory_shim/Dockerfile.cipher
- Changed EXPOSE directive from `3025` to `8081`

### 3. .env.local
- Added `CIPHER_MEMORY_PORT=8081` configuration

## Usage
The Cipher Memory service now uses port 8081 by default. To change the port:
1. Set the `CIPHER_MEMORY_PORT` environment variable to your desired port
2. Restart the Cipher Memory service

## Verification
To verify the port change:
```bash
curl http://localhost:8081/health
```

## Port Allocation Summary
- **Cipher Memory**: 8081 (changed from 8080)
- **MCP Gateway**: 2091
- **Docling MCP**: 3020
- **E2B Runner**: 7071
- **VL Sentinel**: 7072