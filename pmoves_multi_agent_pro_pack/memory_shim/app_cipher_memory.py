#!/usr/bin/env python3
"""
PMOVES Cipher Memory Integration Layer
Integrates Pmoves-cipher memory system with PMOVES MCP architecture.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import tempfile
import shutil

from mcp import Tool
from mcp.server import Server
from mcp.types import TextContent
import mcp.server.stdio

class CipherMemoryManager:
    """Interface to Pmoves-cipher memory system"""

    def __init__(self, cipher_path: str = None):
        self.cipher_path = Path(cipher_path) if cipher_path else Path(__file__).parent / "pmoves_cipher"
        self.cipher_binary = self.cipher_path / "dist" / "src" / "app" / "index.cjs"
        self.config_path = self.cipher_path / "memAgent" / "cipher.yml"
        self.temp_dir = None

    def _ensure_cipher_built(self):
        """Ensure cipher is built and available"""
        if not self.cipher_binary.exists():
            print(f"Building cipher at {self.cipher_path}...")
            try:
                # Install dependencies and build
                subprocess.run(
                    ["pnpm", "install"],
                    cwd=self.cipher_path,
                    check=True,
                    capture_output=True
                )
                subprocess.run(
                    ["pnpm", "run", "build:no-ui"],
                    cwd=self.cipher_path,
                    check=True,
                    capture_output=True
                )
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Failed to build cipher: {e}")
            except FileNotFoundError:
                raise RuntimeError("pnpm not found. Please install Node.js and pnpm")

    def _create_temp_config(self, config_overrides: Dict[str, Any] = None) -> str:
        """Create temporary cipher configuration"""
        self.temp_dir = tempfile.mkdtemp(prefix="pmoves_cipher_")
        
        # Load base config
        with open(self.config_path, 'r') as f:
            config = f.read()
        
        # Apply overrides
        if config_overrides:
            # Simple string replacement for basic overrides
            for key, value in config_overrides.items():
                if key == "llm_provider":
                    config = config.replace("provider: openai", f"provider: {value}")
                elif key == "llm_model":
                    config = config.replace("model: gpt-4.1-mini", f"model: {value}")
                elif key == "api_key":
                    config = config.replace("apiKey: $OPENAI_API_KEY", f"apiKey: {value}")
        
        temp_config_path = os.path.join(self.temp_dir, "cipher.yml")
        with open(temp_config_path, 'w') as f:
            f.write(config)
        
        return temp_config_path

    def _run_cipher_command(self, args: List[str], input_data: str = None) -> str:
        """Run cipher command and return output"""
        self._ensure_cipher_built()
        
        env = os.environ.copy()
        if self.temp_dir:
            env["CIPHER_CONFIG_PATH"] = os.path.join(self.temp_dir, "cipher.yml")
        
        try:
            cmd = ["node", str(self.cipher_binary)] + args
            result = subprocess.run(
                cmd,
                input=input_data,
                text=True,
                capture_output=True,
                env=env,
                timeout=30
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Cipher command failed: {result.stderr}")
            
            return result.stdout
        except subprocess.TimeoutExpired:
            raise RuntimeError("Cipher command timed out")
        finally:
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                self.temp_dir = None

    def store_memory(self, content: str, memory_type: str = "knowledge", 
                    session_id: str = "pmoves_default") -> str:
        """Store memory using cipher"""
        args = ["--mode", "cli", content]
        output = self._run_cipher_command(args)
        return output.strip()

    def search_memory(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search memory using cipher"""
        # Use cipher's memory search capabilities
        args = ["--mode", "cli", f"Search memory for: {query}"]
        output = self._run_cipher_command(args)
        
        # Parse output (simplified - in real implementation would parse structured output)
        results = []
        lines = output.strip().split('\n')
        for line in lines:
            if line.strip():
                results.append({
                    "content": line.strip(),
                    "type": "knowledge",
                    "relevance": 1.0  # Placeholder
                })
        
        return results[:limit]

    def extract_and_operate_memory(self, content: str, operation: str = "add") -> str:
        """Extract knowledge and apply operation using cipher"""
        args = ["--mode", "cli", f"Extract and {operation} this knowledge: {content}"]
        output = self._run_cipher_command(args)
        return output.strip()

    def store_reasoning_memory(self, reasoning: str, context: str = "") -> str:
        """Store reasoning steps using cipher"""
        args = ["--mode", "cli", f"Store reasoning: {reasoning}\nContext: {context}"]
        output = self._run_cipher_command(args)
        return output.strip()

    def search_reasoning_patterns(self, query: str) -> List[Dict[str, Any]]:
        """Search reasoning patterns using cipher"""
        args = ["--mode", "cli", f"Search reasoning patterns for: {query}"]
        output = self._run_cipher_command(args)
        
        # Parse output
        patterns = []
        lines = output.strip().split('\n')
        for line in lines:
            if line.strip():
                patterns.append({
                    "pattern": line.strip(),
                    "type": "reasoning"
                })
        
        return patterns

class CipherMemoryServer:
    """MCP Server for Cipher Memory Integration"""

    def __init__(self):
        self.server = Server("pmoves-cipher-memory")
        self.memory_manager = CipherMemoryManager()

    async def handle_store_memory(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Store memory using cipher"""
        content = arguments["content"]
        memory_type = arguments.get("memory_type", "knowledge")
        session_id = arguments.get("session_id", "pmoves_default")

        try:
            result = self.memory_manager.store_memory(content, memory_type, session_id)
            return [TextContent(
                type="text",
                text=f"Memory stored successfully: {result}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error storing memory: {str(e)}"
            )]

    async def handle_search_memory(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Search memory using cipher"""
        query = arguments["query"]
        limit = arguments.get("limit", 10)

        try:
            results = self.memory_manager.search_memory(query, limit)
            
            if not results:
                return [TextContent(type="text", text="No memories found")]
            
            result_text = f"Found {len(results)} memories:\n\n"
            for i, memory in enumerate(results, 1):
                result_text += f"{i}. {memory['content']}\n"
                result_text += f"   Type: {memory['type']}\n"
                result_text += f"   Relevance: {memory['relevance']}\n\n"
            
            return [TextContent(type="text", text=result_text)]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error searching memory: {str(e)}"
            )]

    async def handle_extract_and_operate_memory(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Extract knowledge and apply operation using cipher"""
        content = arguments["content"]
        operation = arguments.get("operation", "add")

        try:
            result = self.memory_manager.extract_and_operate_memory(content, operation)
            return [TextContent(
                type="text",
                text=f"Memory operation completed: {result}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error with memory operation: {str(e)}"
            )]

    async def handle_store_reasoning_memory(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Store reasoning steps using cipher"""
        reasoning = arguments["reasoning"]
        context = arguments.get("context", "")

        try:
            result = self.memory_manager.store_reasoning_memory(reasoning, context)
            return [TextContent(
                type="text",
                text=f"Reasoning stored successfully: {result}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error storing reasoning: {str(e)}"
            )]

    async def handle_search_reasoning_patterns(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Search reasoning patterns using cipher"""
        query = arguments["query"]

        try:
            patterns = self.memory_manager.search_reasoning_patterns(query)
            
            if not patterns:
                return [TextContent(type="text", text="No reasoning patterns found")]
            
            result_text = f"Found {len(patterns)} reasoning patterns:\n\n"
            for i, pattern in enumerate(patterns, 1):
                result_text += f"{i}. {pattern['pattern']}\n"
                result_text += f"   Type: {pattern['type']}\n\n"
            
            return [TextContent(type="text", text=result_text)]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error searching reasoning patterns: {str(e)}"
            )]

async def main():
    """Main server entry point"""
    server = CipherMemoryServer()

    # Register tools
    @server.server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="cipher_store_memory",
                description="Store memory using Pmoves-cipher system",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Content to store in memory"},
                        "memory_type": {"type": "string", "description": "Type of memory (knowledge, reflection, etc.)", "default": "knowledge"},
                        "session_id": {"type": "string", "description": "Session identifier", "default": "pmoves_default"}
                    },
                    "required": ["content"]
                }
            ),
            Tool(
                name="cipher_search_memory",
                description="Search memory using Pmoves-cipher system",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "limit": {"type": "integer", "description": "Maximum number of results", "default": 10}
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="cipher_extract_and_operate_memory",
                description="Extract knowledge and apply operation using Pmoves-cipher",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Content to extract knowledge from"},
                        "operation": {"type": "string", "description": "Operation to apply (add, update, delete)", "default": "add"}
                    },
                    "required": ["content"]
                }
            ),
            Tool(
                name="cipher_store_reasoning_memory",
                description="Store reasoning steps using Pmoves-cipher",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reasoning": {"type": "string", "description": "Reasoning steps to store"},
                        "context": {"type": "string", "description": "Additional context for the reasoning"}
                    },
                    "required": ["reasoning"]
                }
            ),
            Tool(
                name="cipher_search_reasoning_patterns",
                description="Search reasoning patterns using Pmoves-cipher",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query for reasoning patterns"}
                    },
                    "required": ["query"]
                }
            )
        ]

    # Register tool handlers
    @server.server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        if name == "cipher_store_memory":
            return await server.handle_store_memory(arguments)
        elif name == "cipher_search_memory":
            return await server.handle_search_memory(arguments)
        elif name == "cipher_extract_and_operate_memory":
            return await server.handle_extract_and_operate_memory(arguments)
        elif name == "cipher_store_reasoning_memory":
            return await server.handle_store_reasoning_memory(arguments)
        elif name == "cipher_search_reasoning_patterns":
            return await server.handle_search_reasoning_patterns(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    # Start the server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options()
        )

def start_cipher_ui_mode():
    """Start cipher in UI mode with web interface"""
    import subprocess
    import os
    
    # Set environment variables for UI mode
    env = os.environ.copy()
    env['CIPHER_MODE'] = 'ui'
    env['CIPHER_UI_PORT'] = env.get('CIPHER_UI_PORT', '3010')
    env['CIPHER_API_PORT'] = env.get('CIPHER_API_PORT', '3011')
    
    # Change to cipher directory
    cipher_path = "/app/memory_shim/pmoves_cipher"
    
    print(f"Starting Cipher in UI mode on ports {env['CIPHER_UI_PORT']} (UI) and {env['CIPHER_API_PORT']} (API)")
    
    try:
        # Start cipher in UI mode using Popen to keep it running
        process = subprocess.Popen([
            "node",
            "--preserve-symlinks",
            "memory_shim/pmoves_cipher/dist/src/app/index.cjs",
            "--mode", "ui",
            "--ui-port", env['CIPHER_UI_PORT'],
            "--port", env['CIPHER_API_PORT'],
            "--host", "0.0.0.0",
            "--agent", "memory_shim/pmoves_cipher/memAgent/cipher_pmoves.yml"
        ],
        cwd="/app",
        env={**env, "NODE_PATH": "/app/memory_shim/pmoves_cipher/node_modules"},
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
        )
        
        print("Cipher UI mode started successfully")
        print(f"UI available at: http://localhost:{env['CIPHER_UI_PORT']}")
        print(f"API available at: http://localhost:{env['CIPHER_API_PORT']}")
        
        # Monitor the process and output logs
        try:
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(output.strip())
        except KeyboardInterrupt:
            print("Shutting down Cipher UI mode...")
            process.terminate()
            sys.exit(0)
            
    except Exception as e:
        print(f"Error starting Cipher UI mode: {e}")
        print("Falling back to MCP server mode...")
        asyncio.run(main())

if __name__ == "__main__":
    # Check if we should start in UI mode
    if os.environ.get('CIPHER_UI_MODE', 'false').lower() == 'true':
        start_cipher_ui_mode()
    else:
        asyncio.run(main())