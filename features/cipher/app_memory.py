#!/usr/bin/env python3
"""
PMOVES Memory Layer MCP Server
Based on Pmoves-cipher memory management system.
Provides persistent memory capabilities for multi-agent workflows.
"""

import asyncio
import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib
import uuid

from mcp import Tool
from mcp.server import Server
from mcp.types import TextContent, PromptMessage
import mcp.server.stdio

class MemoryManager:
    """Memory management system with SQLite backend"""

    def __init__(self, db_path: str = "memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database with memory tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    agent_id TEXT,
                    memory_type TEXT,
                    content TEXT,
                    metadata TEXT,
                    timestamp REAL,
                    expires_at REAL,
                    tags TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    created_at REAL,
                    last_accessed REAL,
                    metadata TEXT
                )
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_memories_session ON memories(session_id)
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_memories_timestamp ON memories(timestamp)
            ''')

    def create_session(self, session_name: str, metadata: Dict[str, Any] = None) -> str:
        """Create a new memory session"""
        session_id = str(uuid.uuid4())
        now = datetime.now().timestamp()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO sessions (id, name, created_at, last_accessed, metadata) VALUES (?, ?, ?, ?, ?)",
                (session_id, session_name, now, now, json.dumps(metadata or {}))
            )

        return session_id

    def store_memory(self, session_id: str, agent_id: str, memory_type: str,
                    content: str, metadata: Dict[str, Any] = None,
                    tags: List[str] = None, ttl_seconds: int = None) -> str:
        """Store a memory entry"""
        memory_id = str(uuid.uuid4())
        now = datetime.now().timestamp()
        expires_at = (now + ttl_seconds) if ttl_seconds else None

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO memories
                   (id, session_id, agent_id, memory_type, content, metadata, timestamp, expires_at, tags)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (memory_id, session_id, agent_id, memory_type, content,
                 json.dumps(metadata or {}), now, expires_at, json.dumps(tags or []))
            )

        return memory_id

    def retrieve_memories(self, session_id: str = None, agent_id: str = None,
                         memory_type: str = None, tags: List[str] = None,
                         limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieve memories with optional filtering"""
        query = "SELECT * FROM memories WHERE 1=1"
        params = []

        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)

        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id)

        if memory_type:
            query += " AND memory_type = ?"
            params.append(memory_type)

        if tags:
            tag_conditions = " OR ".join(["json_array_contains(tags, ?)"] * len(tags))
            query += f" AND ({tag_conditions})"
            params.extend([f'"{tag}"' for tag in tags])

        # Exclude expired memories
        now = datetime.now().timestamp()
        query += " AND (expires_at IS NULL OR expires_at > ?)"
        params.append(now)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

        memories = []
        for row in rows:
            memory = dict(row)
            memory['metadata'] = json.loads(memory['metadata'])
            memory['tags'] = json.loads(memory['tags'])
            memories.append(memory)

        return memories

    def update_memory(self, memory_id: str, content: str = None,
                     metadata: Dict[str, Any] = None, tags: List[str] = None) -> bool:
        """Update an existing memory"""
        updates = []
        params = []

        if content is not None:
            updates.append("content = ?")
            params.append(content)

        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata))

        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags))

        if not updates:
            return False

        query = f"UPDATE memories SET {', '.join(updates)} WHERE id = ?"
        params.append(memory_id)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            return cursor.rowcount > 0

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory entry"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            return cursor.rowcount > 0

    def cleanup_expired(self) -> int:
        """Clean up expired memories"""
        now = datetime.now().timestamp()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM memories WHERE expires_at <= ?", (now,))
            return cursor.rowcount

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()

        if row:
            session = dict(row)
            session['metadata'] = json.loads(session['metadata'])
            return session
        return None

class MemoryServer:
    """MCP Server for memory management"""

    def __init__(self):
        self.server = Server("pmoves-memory")
        self.memory_manager = MemoryManager()

    async def handle_create_session(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Create a new memory session"""
        session_name = arguments.get("name", "default")
        metadata = arguments.get("metadata", {})

        session_id = self.memory_manager.create_session(session_name, metadata)

        return [TextContent(
            type="text",
            text=f"Created memory session '{session_name}' with ID: {session_id}"
        )]

    async def handle_store_memory(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Store a memory entry"""
        session_id = arguments["session_id"]
        agent_id = arguments.get("agent_id", "default")
        memory_type = arguments["memory_type"]
        content = arguments["content"]
        metadata = arguments.get("metadata", {})
        tags = arguments.get("tags", [])
        ttl_seconds = arguments.get("ttl_seconds")

        memory_id = self.memory_manager.store_memory(
            session_id, agent_id, memory_type, content, metadata, tags, ttl_seconds
        )

        return [TextContent(
            type="text",
            text=f"Stored memory '{memory_type}' with ID: {memory_id}"
        )]

    async def handle_retrieve_memories(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Retrieve memories with filtering"""
        session_id = arguments.get("session_id")
        agent_id = arguments.get("agent_id")
        memory_type = arguments.get("memory_type")
        tags = arguments.get("tags")
        limit = arguments.get("limit", 50)
        offset = arguments.get("offset", 0)

        memories = self.memory_manager.retrieve_memories(
            session_id, agent_id, memory_type, tags, limit, offset
        )

        if not memories:
            return [TextContent(type="text", text="No memories found")]

        result = f"Retrieved {len(memories)} memories:\n\n"
        for memory in memories:
            result += f"ID: {memory['id']}\n"
            result += f"Type: {memory['memory_type']}\n"
            result += f"Agent: {memory['agent_id']}\n"
            result += f"Time: {datetime.fromtimestamp(memory['timestamp']).isoformat()}\n"
            result += f"Content: {memory['content']}\n"
            if memory['tags']:
                result += f"Tags: {', '.join(memory['tags'])}\n"
            result += "---\n"

        return [TextContent(type="text", text=result)]

    async def handle_update_memory(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Update an existing memory"""
        memory_id = arguments["memory_id"]
        content = arguments.get("content")
        metadata = arguments.get("metadata")
        tags = arguments.get("tags")

        success = self.memory_manager.update_memory(memory_id, content, metadata, tags)

        if success:
            return [TextContent(type="text", text=f"Updated memory {memory_id}")]
        else:
            return [TextContent(type="text", text=f"Memory {memory_id} not found or no changes made")]

    async def handle_delete_memory(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Delete a memory entry"""
        memory_id = arguments["memory_id"]

        success = self.memory_manager.delete_memory(memory_id)

        if success:
            return [TextContent(type="text", text=f"Deleted memory {memory_id}")]
        else:
            return [TextContent(type="text", text=f"Memory {memory_id} not found")]

    async def handle_cleanup_expired(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Clean up expired memories"""
        deleted_count = self.memory_manager.cleanup_expired()

        return [TextContent(
            type="text",
            text=f"Cleaned up {deleted_count} expired memories"
        )]

    async def handle_get_session_info(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Get session information"""
        session_id = arguments["session_id"]

        session = self.memory_manager.get_session_info(session_id)

        if session:
            result = f"Session: {session['name']}\n"
            result += f"ID: {session['id']}\n"
            result += f"Created: {datetime.fromtimestamp(session['created_at']).isoformat()}\n"
            result += f"Last Accessed: {datetime.fromtimestamp(session['last_accessed']).isoformat()}\n"
            if session['metadata']:
                result += f"Metadata: {json.dumps(session['metadata'], indent=2)}\n"
            return [TextContent(type="text", text=result)]
        else:
            return [TextContent(type="text", text=f"Session {session_id} not found")]

async def main():
    """Main server entry point"""
    server = MemoryServer()

    # Register tools
    @server.server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="create_session",
                description="Create a new memory session for organizing memories",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Session name"},
                        "metadata": {"type": "object", "description": "Optional session metadata"}
                    },
                    "required": ["name"]
                }
            ),
            Tool(
                name="store_memory",
                description="Store a memory entry in the system",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"},
                        "agent_id": {"type": "string", "description": "Agent identifier"},
                        "memory_type": {"type": "string", "description": "Type of memory (task, result, context, etc.)"},
                        "content": {"type": "string", "description": "Memory content"},
                        "metadata": {"type": "object", "description": "Optional metadata"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional tags"},
                        "ttl_seconds": {"type": "integer", "description": "Time to live in seconds"}
                    },
                    "required": ["session_id", "memory_type", "content"]
                }
            ),
            Tool(
                name="retrieve_memories",
                description="Retrieve memories with optional filtering",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Filter by session ID"},
                        "agent_id": {"type": "string", "description": "Filter by agent ID"},
                        "memory_type": {"type": "string", "description": "Filter by memory type"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tags"},
                        "limit": {"type": "integer", "description": "Maximum number of results", "default": 50},
                        "offset": {"type": "integer", "description": "Offset for pagination", "default": 0}
                    }
                }
            ),
            Tool(
                name="update_memory",
                description="Update an existing memory entry",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "memory_id": {"type": "string", "description": "Memory ID to update"},
                        "content": {"type": "string", "description": "New content"},
                        "metadata": {"type": "object", "description": "New metadata"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "New tags"}
                    },
                    "required": ["memory_id"]
                }
            ),
            Tool(
                name="delete_memory",
                description="Delete a memory entry",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "memory_id": {"type": "string", "description": "Memory ID to delete"}
                    },
                    "required": ["memory_id"]
                }
            ),
            Tool(
                name="cleanup_expired",
                description="Clean up expired memories",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="get_session_info",
                description="Get information about a memory session",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session ID"}
                    },
                    "required": ["session_id"]
                }
            )
        ]

    # Register tool handlers
    @server.server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        if name == "create_session":
            return await server.handle_create_session(arguments)
        elif name == "store_memory":
            return await server.handle_store_memory(arguments)
        elif name == "retrieve_memories":
            return await server.handle_retrieve_memories(arguments)
        elif name == "update_memory":
            return await server.handle_update_memory(arguments)
        elif name == "delete_memory":
            return await server.handle_delete_memory(arguments)
        elif name == "cleanup_expired":
            return await server.handle_cleanup_expired(arguments)
        elif name == "get_session_info":
            return await server.handle_get_session_info(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    # Start the server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())