#!/usr/bin/env python3
"""
MCP Server wrapper for POWERFULMOVES/docling fork.
This provides an MCP server interface to docling document processing capabilities.
Follows official MCP 1.0+ implementation patterns with proper HTTP transport support.
"""

import asyncio
import json
import logging
import sys
import tempfile
import traceback
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional

# MCP imports - using official MCP 1.0+ patterns
try:
    from mcp.server import Server
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server
    from mcp.server.fastapi import serve_app
    from mcp.types import (
        CallToolRequest,
        CallToolResult,
        ListToolsRequest,
        ListToolsResult,
        TextContent,
        Tool,
        ErrorData,
    )
    import mcp.server.stdio
except ImportError as e:
    print(f"Error: MCP server dependencies not found: {e}")
    print("Please install mcp package: pip install 'mcp>=1.0.0'")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DoclingMCPServer:
    """MCP Server wrapper for docling document processing."""
    
    def __init__(self):
        self.server = Server("docling-mcp")
        self.temp_dir = Path(tempfile.mkdtemp(prefix="docling_mcp_"))
        logger.info(f"Initialized Docling MCP Server with temp directory: {self.temp_dir}")
        
    async def _convert_document(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Convert document using docling (mock implementation for testing)."""
        input_path = arguments.get("input_path")
        output_format = arguments.get("output_format", "markdown")
        ocr = arguments.get("ocr", True)
        tables = arguments.get("tables", True)
        images = arguments.get("images", False)
        
        if not input_path:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: input_path is required")],
                isError=True
            )
        
        try:
            # Mock conversion - in real implementation, this would use docling
            logger.info(f"Mock converting document: {input_path} to {output_format}")
            
            # Simulate conversion process
            await asyncio.sleep(0.1)  # Simulate processing time
            
            result_text = f"""Document conversion completed (mock):
- Input: {input_path}
- Output format: {output_format}
- OCR: {ocr}
- Tables: {tables}
- Images: {images}
- Status: Success (mock implementation)"""
            
            return CallToolResult(
                content=[TextContent(type="text", text=result_text)],
                isError=False
            )
            
        except Exception as e:
            logger.error(f"Document conversion failed: {e}")
            logger.error(traceback.format_exc())
            return CallToolResult(
                content=[TextContent(type="text", text=f"Conversion failed: {str(e)}")],
                isError=True
            )
    
    async def _get_supported_formats(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Get supported formats (mock implementation)."""
        formats_info = {
            "input_formats": ["pdf", "docx", "html", "png", "jpg", "txt"],
            "output_formats": ["markdown", "json", "html", "text"],
            "features": [
                "OCR processing",
                "Table extraction", 
                "Image export",
                "Code enrichment",
                "Formula enrichment",
                "Multiple output formats"
            ]
        }
        
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(formats_info, indent=2))],
            isError=False
        )

    def setup_handlers(self):
        """Setup MCP server handlers."""
        
        @self.server.list_tools()
        async def list_tools():
            """List available tools."""
            return [
                Tool(
                    name="convert_document",
                    description="Convert documents using docling. Supports PDF, DOCX, HTML, images and more formats.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "input_path": {
                                "type": "string",
                                "description": "Path or URL to input document to convert"
                            },
                            "output_format": {
                                "type": "string",
                                "description": "Output format (markdown, json, html, text)",
                                "enum": ["markdown", "json", "html", "text"],
                                "default": "markdown"
                            },
                            "ocr": {
                                "type": "boolean",
                                "description": "Enable OCR processing",
                                "default": True
                            },
                            "tables": {
                                "type": "boolean", 
                                "description": "Enable table structure extraction",
                                "default": True
                            },
                            "images": {
                                "type": "boolean",
                                "description": "Export images",
                                "default": False
                            }
                        },
                        "required": ["input_path"]
                    }
                ),
                Tool(
                    name="get_supported_formats",
                    description="Get list of supported input and output formats",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Handle tool calls."""
            try:
                if name == "convert_document":
                    return await self._convert_document(arguments)
                elif name == "get_supported_formats":
                    return await self._get_supported_formats(arguments)
                else:
                    return CallToolResult(
                        content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                        isError=True
                    )
            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}")
                logger.error(traceback.format_exc())
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")],
                    isError=True
                )

async def run_stdio_server():
    """Run the server with stdio transport."""
    server = DoclingMCPServer()
    server.setup_handlers()
    
    # Start the server
    logger.info("Starting Docling MCP Server with stdio transport...")
    try:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.server.run(
                read_stream,
                write_stream,
                server.server.create_initialization_options()
            )
    except Exception as e:
        logger.error(f"Error running stdio server: {e}")
        logger.error(traceback.format_exc())
        raise

async def run_http_server(host: str = "0.0.0.0", port: int = 3020):
    """Run the server with HTTP transport using FastAPI."""
    server = DoclingMCPServer()
    server.setup_handlers()
    
    # Start the server
    logger.info(f"Starting Docling MCP Server with HTTP transport on {host}:{port}...")
    
    try:
        # Use FastAPI serve_app for HTTP transport
        await serve_app(
            server.server,
            host=host,
            port=port,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Error running HTTP server: {e}")
        logger.error(traceback.format_exc())
        raise

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Docling MCP Server - Document processing MCP server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with stdio transport (default)
  python docling_mcp_server_v2.py --transport stdio
  
  # Run with HTTP transport
  python docling_mcp_server_v2.py --transport streamable-http --host 0.0.0.0 --port 3020
  
  # Run with custom host and port
  python docling_mcp_server_v2.py --transport streamable-http --host localhost --port 8080
        """
    )
    
    parser.add_argument(
        "--transport", 
        choices=["stdio", "streamable-http"], 
        default="stdio",
        help="Transport type to use (default: stdio)"
    )
    parser.add_argument(
        "--host", 
        default="0.0.0.0", 
        help="Host for HTTP transport (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=3020, 
        help="Port for HTTP transport (default: 3020)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    logger.info(f"Starting Docling MCP Server with transport: {args.transport}")
    logger.info(f"Host: {args.host}, Port: {args.port}")
    
    try:
        if args.transport == "stdio":
            asyncio.run(run_stdio_server())
        elif args.transport == "streamable-http":
            asyncio.run(run_http_server(args.host, args.port))
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server failed: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()