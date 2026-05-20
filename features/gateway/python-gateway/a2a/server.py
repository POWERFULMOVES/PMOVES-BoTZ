"""
A2A Server - HTTP server for Agent-to-Agent protocol.

Provides endpoints:
- GET /.well-known/agent.json - Agent Card discovery
- POST /a2a/v1/tasks - JSON-RPC 2.0 task management
- GET /a2a/v1/tasks/{id}/stream - SSE streaming for task updates

Can run standalone or be integrated into the MCP Gateway.

Reference: docs/agents/AI Agent Integration and Best Practices.md
"""

import json
import logging
import os
import queue
import threading
import time
from http.server import BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Any, Callable, Dict, Optional
import http.server


class ThreadingHTTPServer(ThreadingMixIn, http.server.HTTPServer):
    """HTTP Server that handles requests in separate threads for SSE support."""
    daemon_threads = True

from .agent_card import get_agent_card
from .task_handler import TaskHandler
from .types import TaskState

logger = logging.getLogger(__name__)

JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_SECRET = os.environ.get("JWT_SECRET", "").strip()

try:
    from jose import jwt as jose_jwt

    HAS_JOSE = True
except Exception:
    jose_jwt = None
    HAS_JOSE = False


class A2AHTTPHandler(BaseHTTPRequestHandler):
    """HTTP handler for A2A protocol endpoints."""

    # Class-level references (set by server)
    agent_card_provider: Callable[[], Dict] = None
    task_handler: TaskHandler = None
    sse_queues: Dict[str, queue.Queue] = {}
    sse_lock = threading.Lock()

    def _require_auth(self) -> Optional[Dict]:
        """Validate Supabase JWT on protected endpoints (fail-closed)."""
        if not HAS_JOSE:
            self._send_json(500, {"error": "python-jose not installed - JWT validation unavailable"})
            logger.error("python-jose not installed - rejecting request (fail-closed)")
            return None

        if not JWT_SECRET:
            self._send_json(500, {"error": "JWT_SECRET not configured - authentication unavailable"})
            logger.error("JWT_SECRET not set - rejecting request (fail-closed)")
            return None

        auth_header = self.headers.get("Authorization", "")
        if not auth_header:
            self._send_json(401, {"error": "Missing Authorization header"})
            return None

        token = auth_header[7:] if auth_header.startswith("Bearer ") else auth_header
        token = token.strip()
        if not token:
            self._send_json(401, {"error": "Empty token"})
            return None

        try:
            payload = jose_jwt.decode(
                token,
                JWT_SECRET,
                algorithms=[JWT_ALGORITHM],
                options={"verify_signature": True, "verify_aud": False, "verify_exp": True},
            )
        except jose_jwt.ExpiredSignatureError:
            self._send_json(401, {"error": "Token expired"})
            return None
        except jose_jwt.InvalidSignatureError:
            self._send_json(403, {"error": "Invalid token signature"})
            return None
        except jose_jwt.JWTError as exc:
            self._send_json(403, {"error": f"JWT validation failed: {exc}"})
            return None

        if payload.get("role", "") == "anon":
            self._send_json(403, {"error": "Anonymous keys are not permitted"})
            return None

        return payload

    def _send_json(self, status: int, data: Dict) -> None:
        """Send JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def _send_sse_headers(self) -> None:
        """Send SSE response headers."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_OPTIONS(self) -> None:
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self) -> None:
        """Handle GET requests."""
        # Agent Card discovery endpoint
        if self.path == "/.well-known/agent.json":
            if self._require_auth() is None:
                return
            if self.agent_card_provider:
                card = self.agent_card_provider()
                self._send_json(200, card)
            else:
                self._send_json(500, {"error": "Agent card not configured"})
            return

        # Health check
        if self.path == "/a2a/health" or self.path == "/a2a/v1/health":
            self._send_json(200, {
                "status": "healthy",
                "service": "A2A Server",
                "version": "1.0.0",
                "protocol": "a2a/1.0",
            })
            return

        # SSE streaming endpoint for task updates
        if self.path.startswith("/a2a/v1/tasks/") and self.path.endswith("/stream"):
            if self._require_auth() is None:
                return
            task_id = self.path.split("/")[4]
            self._handle_sse_stream(task_id)
            return

        # Task info (GET)
        if self.path.startswith("/a2a/v1/tasks/"):
            if self._require_auth() is None:
                return
            task_id = self.path.split("/")[4]
            if self.task_handler:
                result = self.task_handler.handle_jsonrpc({
                    "jsonrpc": "2.0",
                    "method": "tasks/get",
                    "params": {"task_id": task_id},
                    "id": 1,
                })
                if "error" in result:
                    self._send_json(404, result)
                else:
                    self._send_json(200, result)
            else:
                self._send_json(500, {"error": "Task handler not configured"})
            return

        self._send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        """Handle POST requests."""
        if self.path == "/a2a/v1/tasks" or self.path == "/a2a/tasks":
            if self._require_auth() is None:
                return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else "{}"

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON"})
            return

        # A2A JSON-RPC endpoint
        if self.path == "/a2a/v1/tasks" or self.path == "/a2a/tasks":
            if self.task_handler:
                result = self.task_handler.handle_jsonrpc(data)
                status = 200 if "result" in result else 400
                self._send_json(status, result)
            else:
                self._send_json(500, {"error": "Task handler not configured"})
            return

        self._send_json(404, {"error": "Not found"})

    def _handle_sse_stream(self, task_id: str) -> None:
        """Handle SSE streaming for task updates."""
        if not self.task_handler:
            self._send_json(500, {"error": "Task handler not configured"})
            return

        task = self.task_handler.store.get(task_id)
        if not task:
            self._send_json(404, {"error": f"Task not found: {task_id}"})
            return

        self._send_sse_headers()

        # Create queue for this stream
        stream_queue = queue.Queue()
        with self.sse_lock:
            if task_id not in self.sse_queues:
                self.sse_queues[task_id] = []
            self.sse_queues[task_id].append(stream_queue)

        try:
            # Send initial state
            self._send_sse_event("state", {"state": task.state.value, "task": task.to_dict()})

            # Poll for updates until task completes or client disconnects
            last_updated = task.updated_at
            while task.state not in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
                try:
                    # Check for queued events
                    try:
                        event = stream_queue.get(timeout=1.0)
                        self._send_sse_event(event["type"], event["data"])
                    except queue.Empty:
                        pass

                    # Check for task updates
                    task = self.task_handler.store.get(task_id)
                    if task and task.updated_at != last_updated:
                        last_updated = task.updated_at
                        self._send_sse_event("update", task.to_dict())

                    # Send keepalive
                    self._send_sse_event("ping", {"timestamp": time.time()})

                except (BrokenPipeError, ConnectionResetError):
                    break

            # Send final state
            if task:
                self._send_sse_event("complete", task.to_dict())

        finally:
            # Clean up queue
            with self.sse_lock:
                if task_id in self.sse_queues:
                    try:
                        self.sse_queues[task_id].remove(stream_queue)
                    except ValueError:
                        pass
                    if not self.sse_queues[task_id]:
                        del self.sse_queues[task_id]

    def _send_sse_event(self, event_type: str, data: Any) -> None:
        """Send an SSE event."""
        try:
            event = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
            self.wfile.write(event.encode())
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            # Client disconnected - expected during SSE streaming
            raise
        except Exception as e:
            logger.warning(f"SSE write failed for event {event_type}: {e}")

    def log_message(self, format: str, *args) -> None:
        """Log HTTP requests."""
        logger.info(f"{self.address_string()} - {format % args}")


def create_a2a_server(
    host: str = "0.0.0.0",
    port: int = 7000,
    tool_executor: Optional[Callable[[str, Dict], Dict]] = None,
    upstream_servers: Optional[Dict] = None,
) -> ThreadingHTTPServer:
    """
    Create an A2A HTTP server with threading support for SSE.

    Args:
        host: Bind address
        port: Port number
        tool_executor: Callable for executing MCP tools
        upstream_servers: Dict of upstream MCP servers for agent card

    Returns:
        Configured ThreadingHTTPServer instance
    """
    # Configure handler
    if tool_executor:
        A2AHTTPHandler.task_handler = TaskHandler(tool_executor)

    if upstream_servers:
        def card_provider():
            return get_agent_card(upstream_servers).to_dict()
        A2AHTTPHandler.agent_card_provider = card_provider

    server = ThreadingHTTPServer((host, port), A2AHTTPHandler)
    logger.info(f"A2A Server configured on {host}:{port} (threaded)")
    return server


def run_standalone(
    host: str = "0.0.0.0",
    port: int = 7000,
) -> None:
    """Run A2A server standalone (for testing)."""
    # Mock tool executor
    def mock_executor(tool_name: str, arguments: Dict) -> Dict:
        return {
            "result": {
                "content": [{"type": "text", "text": f"Mock result for {tool_name}"}]
            }
        }

    # Mock upstream servers
    mock_servers = {
        "test-server": {"transport": "http", "url": "http://localhost:8080"}
    }

    server = create_a2a_server(
        host=host,
        port=port,
        tool_executor=mock_executor,
        upstream_servers=mock_servers,
    )

    logger.info(f"Starting standalone A2A Server on {host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down A2A Server...")
        server.shutdown()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    run_standalone(
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("A2A_PORT", "7000")),
    )
