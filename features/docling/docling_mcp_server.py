#!/usr/bin/env python3
"""
MCP Server wrapper for POWERFULMOVES/docling fork.
This provides an MCP server interface to docling document processing capabilities.
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
    import mcp.server.stdio
except ImportError:
    print("Error: MCP server dependencies not found. Please install mcp package.")
    sys.exit(1)

# Docling imports
try:
    from docling.cli.main import convert
    from docling.datamodel.base_models import ConversionStatus, InputFormat, OutputFormat
    from docling.document_converter import DocumentConverter
except ImportError:
    print("Error: Docling dependencies not found. Please ensure docling submodule is available.")
    sys.exit(1)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DoclingMCPServer:
    """MCP Server wrapper for docling document processing."""
    
    def __init__(self):
        self.server = Server("docling-mcp")
        self.temp_dir = Path(tempfile.mkdtemp(prefix="docling_mcp_"))
        
    async def _convert_document(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Convert document using docling."""
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
            # Create output directory
            output_dir = self.temp_dir / "output"
            output_dir.mkdir(exist_ok=True)
            
            # Prepare docling arguments
            docling_args = [
                input_path,
                "--to", output_format,
                "--output", str(output_dir),
                "--no-logo"  # Skip logo for cleaner output
            ]
            
            if ocr:
                docling_args.extend(["--ocr"])
            if tables:
                docling_args.extend(["--tables"])
            if images:
                docling_args.extend(["--images"])
            
            # Run docling conversion
            logger.info(f"Converting document: {input_path} to {output_format}")
            
            # Use docling's convert function directly
            import sys
            from unittest.mock import patch
            
            # Mock sys.argv for docling convert function
            with patch.object(sys, 'argv', ['docling'] + docling_args):
                convert(
                    input_sources=[input_path],
                    to_formats=[OutputFormat[output_format.upper()]],
                    output=output_dir,
                    ocr=ocr,
                    tables=tables,
                    image_export_mode="embedded" if images else "placeholder"
                )
            
            # Read and return results
            result_files = []
            for file_path in output_dir.glob("*"):
                if file_path.is_file():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            result_files.append({
                                "filename": file_path.name,
                                "content": content,
                                "size": len(content)
                            })
                    except UnicodeDecodeError:
                        # Handle binary files
                        with open(file_path, 'rb') as f:
                            content = f.read()
                            result_files.append({
                                "filename": file_path.name,
                                "content": f"<binary data, size: {len(content)} bytes>",
                                "size": len(content),
                                "binary": True
                            })
            
            result_text = f"Document conversion completed. Generated {len(result_files)} files:\n"
            for file_info in result_files:
                result_text += f"- {file_info['filename']} ({file_info['size']} bytes)\n"
            
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
        """Get supported formats."""
        formats_info = {
            "input_formats": [fmt.value for fmt in InputFormat],
            "output_formats": [fmt.value for fmt in OutputFormat],
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

async def run_stdio_server(server: DoclingMCPServer):
    """Run the server with stdio transport."""
    server.setup_handlers()
    
    # Start the server
    logger.info("Starting Docling MCP Server with stdio transport...")
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options()
        )

async def run_http_server(server: DoclingMCPServer, host: str = "0.0.0.0", port: int = 3020):
    """Run the server with HTTP transport using SSE."""
    server.setup_handlers()
    
    # Start the server
    logger.info(f"Starting Docling MCP Server with HTTP transport on {host}:{port}...")
    
    try:
        # Create SSE transport with proper endpoint
        transport = SseServerTransport('/mcp')
        
        # For SSE transport, we use the standard Server.run() method
        # The transport provides the necessary streams for HTTP communication
        logger.info(f"SSE transport created with endpoint: /mcp")
        logger.info(f"HTTP server should be accessible at http://{host}:{port}/mcp")
        
        # Run the server with the SSE transport (correct parameter order)
        await server.server.run(
            transport,
            server.server.create_initialization_options()
        )
        
    except Exception as e:
        logger.error(f"Error running HTTP server: {e}")
        logger.error(traceback.format_exc())
        raise

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Docling MCP Server")
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio",
                       help="Transport type to use")
    parser.add_argument("--host", default="0.0.0.0", help="Host for HTTP transport")
    parser.add_argument("--port", type=int, default=3020, help="Port for HTTP transport")
    
    args = parser.parse_args()
    
    server = DoclingMCPServer()
    
    if args.transport == "stdio":
        asyncio.run(run_stdio_server(server))
    elif args.transport == "streamable-http":
        asyncio.run(run_http_server(server, args.host, args.port))

if __name__ == "__main__":
    main()
