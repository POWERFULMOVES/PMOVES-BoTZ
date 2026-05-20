"""
JWT Authentication for MCP SSE Endpoints

Provides JWT validation using Supabase JWT secret for MCP server authentication.

Usage:
    from features.mcp_bridge.auth import validate_jwt_token, require_auth

    # FastAPI example
    @app.get("/sse")
    async def sse_endpoint(request: Request):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "")
        is_valid, payload = validate_jwt_token(token)
        if not is_valid:
            raise HTTPException(status_code=401, detail="Invalid token")
"""

import os
from typing import Tuple, Dict, Any, Optional

from fastapi import HTTPException

try:
    from jose import jwt
    HAS_JOSE = True
except ImportError:
    HAS_JOSE = False
    jwt = None

# Supabase JWT secret (shared with PMOVES.AI)
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"


def validate_jwt_token(token: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Validate a JWT token using Supabase JWT secret.

    Args:
        token: JWT token string

    Returns:
        Tuple of (is_valid, payload, message)
        - is_valid: True if token is valid
        - payload: Decoded JWT payload if valid, None otherwise
        - message: Status message

    Valid tokens:
    - Must have valid signature (if JWT_SECRET is set)
    - Can be service_role or authenticated user token
    - Rejects anon keys (public keys with limited permissions)
    """
    if not token:
        return False, None, "MISSING_TOKEN"

    if not HAS_JOSE:
        raise HTTPException(
            status_code=500,
            detail="python-jose not installed — JWT validation unavailable"
        )

    if not JWT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="JWT_SECRET not configured — authentication unavailable"
        )

    try:
        # Decode and verify signature
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={
                "verify_signature": True,
                "verify_aud": False,
                "verify_exp": True,
            }
        )

        # Check role - reject anon keys
        role = payload.get("role", "")
        if role == "anon":
            return False, payload, "ANON_KEY_REJECTED"

        # Accept service_role and authenticated user tokens
        return True, payload, "VALID_TOKEN"

    except jwt.ExpiredSignatureError:
        return False, None, "TOKEN_EXPIRED"
    except jwt.InvalidSignatureError:
        return False, None, "INVALID_SIGNATURE"
    except jwt.JWTError as e:
        return False, None, f"JWT_ERROR: {str(e)}"
    except Exception as e:
        return False, None, f"ERROR: {str(e)}"


def require_auth(auth_header: str = "") -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Validate Authorization header and extract token.

    Args:
        auth_header: Authorization header value (e.g., "Bearer <token>")

    Returns:
        Tuple of (is_valid, payload, message)
    """
    if not auth_header:
        return False, None, "MISSING_AUTH_HEADER"

    # Extract token from "Bearer <token>" format
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Remove "Bearer " prefix
    else:
        token = auth_header

    return validate_jwt_token(token)


def check_query_token(token: Optional[str]) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Validate token from query parameter.

    Args:
        token: Token from query string

    Returns:
        Tuple of (is_valid, payload, message)
    """
    if not token:
        return False, None, "MISSING_TOKEN"

    return validate_jwt_token(token)
