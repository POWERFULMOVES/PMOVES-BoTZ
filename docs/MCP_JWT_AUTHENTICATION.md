# MCP JWT Authentication

## Overview

PMOVES-BoTZ MCP servers support JWT authentication using the Supabase JWT secret. This provides a unified authentication mechanism across all MCP endpoints.

## Architecture

```
┌─────────────────┐     Bearer Token      ┌──────────────────┐
│   MCP Client    │ ─────────────────────► │   MCP Server     │
│  (Agent Zero)   │                       │  (SSE Endpoint)   │
└─────────────────┘                       └──────────────────┘
                                                     │
                                                     ▼
                                        ┌─────────────────────────┐
                                        │  validate_jwt_token()   │
                                        │  - Verifies signature   │
                                        │  - Checks role         │
                                        │  - Rejects anon keys   │
                                        └─────────────────────────┘
                                                     │
                                                     ▼
                                        ┌─────────────────────────┐
                                        │   SUPABASE_JWT_SECRET   │
                                        │   (Environment Var)    │
                                        └─────────────────────────┘
```

## Configuration

Set the `SUPABASE_JWT_SECRET` environment variable:

```bash
# In .env file
SUPABASE_JWT_SECRET=your-jwt-secret-here

# Or export directly
export SUPABASE_JWT_SECRET=your-jwt-secret-here
```

## Usage

### 1. Generating a JWT Token

For development, you can generate a test token:

```python
from jose import jwt
import time

payload = {
    "role": "service_role",  # or user-specific claims
    "iss": "supabase",
    "iat": int(time.time()),
    "exp": int(time.time()) + 3600,  # 1 hour expiry
}

secret = "your-jwt-secret-here"
token = jwt.encode(payload, secret, algorithm="HS256")
print(f"Bearer {token}")
```

### 2. MCP Client Configuration

When connecting to MCP SSE endpoints, include the JWT token:

**Option A: Authorization Header**
```python
import httpx

async with httpx.AsyncClient() as client:
    await client.get(
        "http://localhost:3020/sse",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )
```

**Option B: Query Parameter**
```python
await client.get(
    "http://localhost:3020/sse",
    params={"token": token}
)
```

### 3. MCP Server Implementation

Add authentication to your MCP SSE endpoint:

```python
from fastapi import FastAPI, Request, HTTPException
from features.mcp_bridge.auth import validate_jwt_token

app = FastAPI()

@app.get("/sse")
async def sse_endpoint(request: Request):
    # Get token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        # Fall back to query parameter
        token = request.query_params.get("token", "")

    # Validate token
    is_valid, payload, message = validate_jwt_token(token)
    if not is_valid:
        raise HTTPException(status_code=401, detail=message)

    # Return SSE stream
    return EventSourceResponse(...)
```

## Token Roles

The JWT validation accepts the following roles:

| Role | Description | Access Level |
|------|-------------|--------------|
| `service_role` | Supabase service role key | Full access |
| `authenticated` | Authenticated user token | User-scoped access |
| `anon` | Public key | **REJECTED** |

## Security Considerations

1. **Network Isolation**: In production, MCP endpoints should only be accessible within the PMOVES internal network (`pmoves_api` tier).

2. **Token Expiry**: JWT tokens should have reasonable expiry times (e.g., 1 hour for service tokens).

3. **Secret Rotation**: Regularly rotate `SUPABASE_JWT_SECRET` in production.

4. **Development Mode**: If no JWT secret is configured, authentication is skipped (for local development).

## Auth Module Reference

### `validate_jwt_token(token: str) -> Tuple[bool, Optional[Dict], str]`

Validates a JWT token using Supabase JWT secret.

**Parameters:**
- `token`: JWT token string

**Returns:**
- `is_valid`: True if token is valid
- `payload`: Decoded JWT payload if valid
- `message`: Status message ("VALID_TOKEN", "TOKEN_EXPIRED", etc.)

### `require_auth(auth_header: str) -> Tuple[bool, Optional[Dict], str]`

Validates Authorization header and extracts token.

**Parameters:**
- `auth_header`: Authorization header value (e.g., "Bearer <token>")

**Returns:** Same as `validate_jwt_token`

### `check_query_token(token: Optional[str]) -> Tuple[bool, Optional[Dict], str]`

Validates token from query parameter.

**Parameters:**
- `token`: Token from query string

**Returns:** Same as `validate_jwt_token`

## MCP Catalog Configuration

The `core/mcp/catalog.yml` documents which authentication method each server uses:

```yaml
mcpServers:
  docling:
    url: http://localhost:3020/sse
    transport: sse
    # Authentication: Bearer token or ?token=
```

## Testing

```bash
# Generate a test token
python3 -c "
from jose import jwt
import time
payload = {'role': 'service_role', 'iss': 'supabase', 'exp': time.time()+3600}
print(jwt.encode(payload, 'your-secret', algorithm='HS256'))
"

# Test with curl
curl -H "Authorization: Bearer <token>" http://localhost:3020/sse
```

## Troubleshooting

**Error: "MISSING_TOKEN"**
- No token provided in Authorization header or query parameter

**Error: "TOKEN_EXPIRED"**
- Token has exceeded its expiry time

**Error: "INVALID_SIGNATURE"**
- Token signed with wrong secret (check SUPABASE_JWT_SECRET)

**Error: "ANON_KEY_REJECTED"**
- Anon keys are not accepted for MCP authentication

**Error: "VALIDATION_UNAVAILABLE"**
- Install python-jose: `pip install python-jose[cryptography]`

## References

- Supabase JWT: https://supabase.com/docs/guides/auth
- python-jose: https://python-jose.readthedocs.io/
- MCP Protocol: https://modelcontextprotocol.io/
