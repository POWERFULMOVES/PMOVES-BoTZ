#!/usr/bin/env python3
"""
PMOVES VPN MCP Server
Exposes Headscale VPN and RustDesk remote desktop tools via MCP

This server provides MCP tools for:
- Listing VPN nodes (Headscale machines)
- Creating VPN authentication keys
- Advertising VPN routes
- Starting/ending remote desktop sessions
- Listing active remote sessions

Integration:
- Headscale API for VPN management
- Supabase for session logging
- NATS for event coordination
"""

import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

# MCP imports
try:
    from mcp.server import Server
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server
    from mcp.server.sse import SseServerTransport
    from mcp.types import (
        CallToolRequest,
        CallToolResult,
        ListToolsRequest,
        ListToolsResult,
        TextContent,
        Tool,
    )
except ImportError:
    print("Error: MCP server dependencies not found. Please install mcp package.")
    sys.exit(1)

# HTTP client imports
try:
    import httpx
except ImportError:
    print("Error: httpx not found. Please install httpx package.")
    sys.exit(1)

# NATS imports (optional)
try:
    import nats
    from nats.js.api import StreamConfig, ConsumerConfig
except ImportError:
    nats = None

# =============================================================================
# Configuration
# =============================================================================
HEADSCALE_URL = os.getenv("HEADSCALE_URL", "http://headscale:8096")
HEADSCALE_API_KEY = os.getenv("HEADSCALE_API_KEY", "")
RUSTDESK_HBBS_URL = os.getenv("RUSTDESK_HBBS_URL", "http://rustdesk-hbbs:21118")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")
NATS_USER = os.getenv("NATS_USER", "pmoves")
NATS_PASS = os.getenv("NATS_PASS", "pmoves")

# Setup logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VPNMCPError(Exception):
    """Base exception for VPN MCP errors."""
    pass


class HeadscaleAPIError(VPNMCPError):
    """Headscale API error."""
    pass


class SupabaseError(VPNMCPError):
    """Supabase API error."""
    pass


class VPNMCPServer:
    """MCP Server for VPN and Remote Desktop management."""

    def __init__(self):
        self.server = Server("pmoves-vpn-manager")
        self.http_client: Optional[httpx.AsyncClient] = None
        self.ncs: Optional[nats.NATS] = None

    async def get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(
                timeout=30.0,
                headers={"Authorization": f"Bearer {HEADSCALE_API_KEY}"}
            )
        return self.http_client

    async def get_nats_connection(self):
        """Get or create NATS connection."""
        if nats is None:
            logger.warning("NATS library not available")
            return None

        if self.ncs is None:
            try:
                self.ncs = await nats.connect(
                    NATS_URL.replace("nats://", f"nats://{NATS_USER}:{NATS_PASS}@")
                )
                logger.info(f"Connected to NATS at {NATS_URL}")
            except Exception as e:
                logger.warning(f"Failed to connect to NATS: {e}")
        return self.ncs

    async def publish_nats_event(self, subject: str, data: Dict[str, Any]):
        """Publish event to NATS."""
        nats_conn = await self.get_nats_connection()
        if nats_conn:
            try:
                await nats_conn.publish(subject, json.dumps(data).encode())
                logger.info(f"Published to {subject}: {data}")
            except Exception as e:
                logger.warning(f"Failed to publish NATS event: {e}")

    async def call_headscale(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Make API call to Headscale."""
        client = await self.get_http_client()
        url = f"{HEADSCALE_URL}{path}"

        try:
            if method.upper() == "GET":
                response = await client.get(url, **kwargs)
            elif method.upper() == "POST":
                response = await client.post(url, **kwargs)
            elif method.upper() == "DELETE":
                response = await client.delete(url, **kwargs)
            elif method.upper() == "PATCH":
                response = await client.patch(url, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HeadscaleAPIError(f"Headscale API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise HeadscaleAPIError(f"Failed to call Headscale: {str(e)}")

    async def call_supabase(self, method: str, table: str, **kwargs) -> Dict[str, Any]:
        """Make API call to Supabase."""
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise SupabaseError("Supabase credentials not configured")

        client = await self.get_http_client()
        url = f"{SUPABASE_URL}/rest/v1/{table}"

        headers = {
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json"
        }

        try:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers, **kwargs)
            elif method.upper() == "POST":
                response = await client.post(url, headers=headers, **kwargs)
            elif method.upper() == "PATCH":
                response = await client.patch(url, headers=headers, **kwargs)
            elif method.upper() == "DELETE":
                response = await client.delete(url, headers=headers, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise SupabaseError(f"Supabase API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise SupabaseError(f"Failed to call Supabase: {str(e)}")

    # =============================================================================
    # Tool Implementations
    # =============================================================================

    async def _vpn_list_nodes(self, arguments: Dict[str, Any]) -> CallToolResult:
        """List all connected VPN nodes."""
        try:
            online_only = arguments.get("online_only", False)
            tag_filter = arguments.get("tag")

            # Fetch machines from Headscale
            data = await self.call_headscale("GET", "/api/v1/machines")

            machines = data.get("machines", data) if isinstance(data, dict) else data

            # Filter by online status
            if online_only:
                machines = [m for m in machines if m.get("online", False)]

            # Filter by tag
            if tag_filter:
                machines = [m for m in machines if tag_filter in m.get("tags", [])]

            result = {
                "count": len(machines),
                "nodes": [
                    {
                        "id": m.get("id"),
                        "hostname": m.get("given_name", m.get("name", "unknown")),
                        "online": m.get("online", False),
                        "ips": m.get("ip_addresses", []),
                        "tags": m.get("tags", []),
                        "last_seen": m.get("last_seen"),
                        "created_at": m.get("created_at"),
                    }
                    for m in machines
                ]
            }

            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(result, indent=2))],
                isError=False
            )

        except HeadscaleAPIError as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error listing VPN nodes: {str(e)}")],
                isError=True
            )
        except Exception as e:
            logger.error(f"Error in vpn_list_nodes: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unexpected error: {str(e)}")],
                isError=True
            )

    async def _vpn_create_auth_key(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Create a VPN authentication key."""
        try:
            user = arguments.get("user")
            if not user:
                return CallToolResult(
                    content=[TextContent(type="text", text="Error: 'user' parameter is required")],
                    isError=True
                )

            tags = arguments.get("tags", ["tag:pmoves"])
            ephemeral = arguments.get("ephemeral", False)
            reusable = not ephemeral
            expiration = arguments.get("expiration")  # e.g., "24h", "7d"

            payload = {
                "user": user,
                "tags": tags,
                "ephemeral": ephemeral,
                "reusable": reusable
            }

            if expiration:
                payload["expiration"] = expiration

            # Create key via Headscale API
            data = await self.call_headscale("POST", "/api/v1/apikey", json=payload)

            # Publish NATS event
            await self.publish_nats_event("vpn.auth_key.created.v1", {
                "key_id": data.get("prefix", "") + "...",
                "user": user,
                "tags": tags,
                "ephemeral": ephemeral,
                "created_at": datetime.utcnow().isoformat()
            })

            # Store in Supabase if not ephemeral
            if not ephemeral and SUPABASE_URL:
                try:
                    await self.call_supabase("POST", "vpn_auth_keys", json={
                        "key_id": data.get("prefix", ""),
                        "user_id": arguments.get("user_id"),  # Optional Supabase user ID
                        "tags": tags,
                        "ephemeral": ephemeral
                    })
                except SupabaseError as e:
                    logger.warning(f"Failed to store auth key in Supabase: {e}")

            result = {
                "key": data.get("key", ""),
                "prefix": data.get("prefix", ""),
                "user": user,
                "tags": tags,
                "ephemeral": ephemeral,
                "expires_at": data.get("expiration"),
                "message": "Use this key to register a device with Headscale"
            }

            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(result, indent=2))],
                isError=False
            )

        except HeadscaleAPIError as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error creating auth key: {str(e)}")],
                isError=True
            )
        except Exception as e:
            logger.error(f"Error in vpn_create_auth_key: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unexpected error: {str(e)}")],
                isError=True
            )

    async def _vpn_advertise_route(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Advertise a VPN route from a node."""
        try:
            node_id = arguments.get("node_id")
            route = arguments.get("route")

            if not node_id or not route:
                return CallToolResult(
                    content=[TextContent(type="text", text="Error: 'node_id' and 'route' are required")],
                    isError=True
                )

            # Advertise route via Headscale API
            data = await self.call_headscale("POST", "/api/v1/routes", json={
                "machine": node_id,
                "route": route,
                "enabled": True
            })

            result = {
                "node_id": node_id,
                "route": route,
                "enabled": True,
                "message": "Route advertised successfully"
            }

            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(result, indent=2))],
                isError=False
            )

        except HeadscaleAPIError as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error advertising route: {str(e)}")],
                isError=True
            )
        except Exception as e:
            logger.error(f"Error in vpn_advertise_route: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unexpected error: {str(e)}")],
                isError=True
            )

    async def _remote_start_session(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Start a remote desktop session."""
        try:
            target_device = arguments.get("target_device")
            user_id = arguments.get("user_id")
            connection_type = arguments.get("connection_type", "rustdesk")

            if not target_device or not user_id:
                return CallToolResult(
                    content=[TextContent(type="text", text="Error: 'target_device' and 'user_id' are required")],
                    isError=True
                )

            session_id = str(uuid.uuid4())

            # Log to Supabase
            if SUPABASE_URL:
                await self.call_supabase("POST", "remote_sessions", json={
                    "session_id": session_id,
                    "user_id": user_id,
                    "target_device": target_device,
                    "connection_type": connection_type,
                    "status": "active"
                })

            # Publish NATS event
            await self.publish_nats_event("remote.session.started.v1", {
                "session_id": session_id,
                "user_id": str(user_id),
                "target_device": target_device,
                "connection_type": connection_type,
                "timestamp": datetime.utcnow().isoformat()
            })

            result = {
                "session_id": session_id,
                "target_device": target_device,
                "connection_type": connection_type,
                "status": "active",
                "message": "Session started successfully",
                "connection_info": {
                    "rustdesk_id": f"{target_device}@headscale.pmoves.local:21118" if connection_type == "rustdesk" else None,
                    "vpn_ip": target_device if connection_type == "vpn" else None
                }
            }

            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(result, indent=2))],
                isError=False
            )

        except SupabaseError as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error starting session: {str(e)}")],
                isError=True
            )
        except Exception as e:
            logger.error(f"Error in remote_start_session: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unexpected error: {str(e)}")],
                isError=True
            )

    async def _remote_end_session(self, arguments: Dict[str, Any]) -> CallToolResult:
        """End a remote desktop session."""
        try:
            session_id = arguments.get("session_id")
            if not session_id:
                return CallToolResult(
                    content=[TextContent(type="text", text="Error: 'session_id' is required")],
                    isError=True
                )

            # Update Supabase
            if SUPABASE_URL:
                await self.call_supabase("PATCH", "remote_sessions", params={
                    "session_id": f"eq.{session_id}"
                }, json={
                    "status": "ended",
                    "ended_at": datetime.utcnow().isoformat()
                })

            # Publish NATS event
            await self.publish_nats_event("remote.session.ended.v1", {
                "session_id": session_id,
                "terminated_by": arguments.get("terminated_by", "user"),
                "timestamp": datetime.utcnow().isoformat()
            })

            result = {
                "session_id": session_id,
                "status": "ended",
                "message": "Session ended successfully"
            }

            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(result, indent=2))],
                isError=False
            )

        except SupabaseError as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error ending session: {str(e)}")],
                isError=True
            )
        except Exception as e:
            logger.error(f"Error in remote_end_session: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unexpected error: {str(e)}")],
                isError=True
            )

    async def _remote_list_sessions(self, arguments: Dict[str, Any]) -> CallToolResult:
        """List active remote desktop sessions."""
        try:
            user_id = arguments.get("user_id")
            status = arguments.get("status", "active")

            if not SUPABASE_URL:
                return CallToolResult(
                    content=[TextContent(type="text", text="Error: Supabase not configured")],
                    isError=True
                )

            # Build query params
            params = {}
            if user_id:
                params["user_id"] = f"eq.{user_id}"
            if status != "all":
                params["status"] = f"eq.{status}"

            # Query Supabase
            sessions = await self.call_supabase("GET", "remote_sessions", params=params)

            result = {
                "count": len(sessions) if isinstance(sessions, list) else 0,
                "sessions": sessions if isinstance(sessions, list) else []
            }

            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(result, indent=2))],
                isError=False
            )

        except SupabaseError as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error listing sessions: {str(e)}")],
                isError=True
            )
        except Exception as e:
            logger.error(f"Error in remote_list_sessions: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unexpected error: {str(e)}")],
                isError=True
            )

    # =============================================================================
    # MCP Server Setup
    # =============================================================================

    async def list_tools(self) -> List[Tool]:
        """List available tools."""
        return [
            Tool(
                name="vpn_list_nodes",
                description="List all connected VPN nodes with status, IPs, and tags",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "online_only": {
                            "type": "boolean",
                            "description": "Filter to only online nodes",
                            "default": False
                        },
                        "tag": {
                            "type": "string",
                            "description": "Filter nodes by tag (e.g., 'tag:admin')"
                        }
                    }
                }
            ),
            Tool(
                name="vpn_create_auth_key",
                description="Create a VPN authentication key for a new device",
                inputSchema={
                    "type": "object",
                    "required": ["user"],
                    "properties": {
                        "user": {
                            "type": "string",
                            "description": "Username for this key (e.g., 'user@pmoves.local')"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags to assign (e.g., ['tag:pmoves', 'tag:support'])",
                            "default": ["tag:pmoves"]
                        },
                        "ephemeral": {
                            "type": "boolean",
                            "description": "If true, key is single-use",
                            "default": False
                        },
                        "expiration": {
                            "type": "string",
                            "description": "Expiration time (e.g., '24h', '7d', '90d')"
                        }
                    }
                }
            ),
            Tool(
                name="vpn_advertise_route",
                description="Advertise a VPN route from a node",
                inputSchema={
                    "type": "object",
                    "required": ["node_id", "route"],
                    "properties": {
                        "node_id": {
                            "type": "string",
                            "description": "Headscale node ID (machine ID)"
                        },
                        "route": {
                            "type": "string",
                            "description": "CIDR range (e.g., '172.30.0.0/24')"
                        }
                    }
                }
            ),
            Tool(
                name="remote_start_session",
                description="Start a remote desktop session",
                inputSchema={
                    "type": "object",
                    "required": ["target_device", "user_id"],
                    "properties": {
                        "target_device": {
                            "type": "string",
                            "description": "Device hostname or ID"
                        },
                        "user_id": {
                            "type": "string",
                            "description": "Requesting user ID (Supabase auth UUID)"
                        },
                        "connection_type": {
                            "type": "string",
                            "enum": ["rustdesk", "vpn", "direct"],
                            "description": "Connection method",
                            "default": "rustdesk"
                        }
                    }
                }
            ),
            Tool(
                name="remote_end_session",
                description="End a remote desktop session",
                inputSchema={
                    "type": "object",
                    "required": ["session_id"],
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Session ID to end"
                        },
                        "terminated_by": {
                            "type": "string",
                            "description": "Who terminated (user, admin, timeout)",
                            "default": "user"
                        }
                    }
                }
            ),
            Tool(
                name="remote_list_sessions",
                description="List active remote desktop sessions",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "Filter by user ID"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["active", "ended", "all"],
                            "default": "active"
                        }
                    }
                }
            )
        ]

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle tool calls."""
        logger.info(f"Tool called: {name} with arguments: {arguments}")

        tool_handlers = {
            "vpn_list_nodes": self._vpn_list_nodes,
            "vpn_create_auth_key": self._vpn_create_auth_key,
            "vpn_advertise_route": self._vpn_advertise_route,
            "remote_start_session": self._remote_start_session,
            "remote_end_session": self._remote_end_session,
            "remote_list_sessions": self._remote_list_sessions,
        }

        handler = tool_handlers.get(name)
        if handler:
            return await handler(arguments)
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True
            )

    async def cleanup(self):
        """Cleanup resources."""
        if self.http_client:
            await self.http_client.aclose()
        if self.ncs:
            await self.ncs.close()


# =============================================================================
# Main Entry Point
# =============================================================================

async def main():
    """Main entry point for the VPN MCP server."""
    server = VPNMCPServer()

    async def handle_list_tools() -> List[Tool]:
        return await server.list_tools()

    async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
        return await server.call_tool(name, arguments)

    # Setup MCP server
    mcp_server = Server("pmoves-vpn-manager")

    @mcp_server.list_tools()
    async def list_tools_handler():
        return await handle_list_tools()

    @mcp_server.call_tool()
    async def call_tool_handler(name: str, arguments: Dict[str, Any]):
        return await handle_call_tool(name, arguments)

    # Determine transport mode
    transport_mode = os.getenv("MCP_TRANSPORT", "stdio")

    try:
        if transport_mode == "sse":
            # SSE transport mode
            from starlette.applications import Starlette
            from starlette.routing import Route
            import uvicorn

            async def sse_endpoint(request):
                async with SseServerTransport("/messages") as (read_stream, write_stream):
                    await mcp_server.run(
                        read_stream,
                        write_stream,
                        mcp_server.create_initialization_options()
                    )

            app = Starlette(routes=[Route("/sse", sse_endpoint)])
            port = int(os.getenv("MCP_PORT", "8110"))
            logger.info(f"Starting VPN MCP server with SSE transport on port {port}")

            config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
            server = uvicorn.Server(config)
            await server.serve()

        else:
            # STDIO transport mode (default)
            logger.info("Starting VPN MCP server with STDIO transport")

            async with stdio_server() as (read_stream, write_stream):
                await mcp_server.run(
                    read_stream,
                    write_stream,
                    mcp_server.create_initialization_options()
                )

    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        await server.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
