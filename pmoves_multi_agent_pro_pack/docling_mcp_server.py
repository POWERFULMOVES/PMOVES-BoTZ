#!/usr/bin/env python3
"""
Docling MCP Server - Fixed with Official MCP Patterns and Configuration Management

This server provides document processing capabilities through the Model Context Protocol (MCP)
using official implementation patterns from the MCP specification with externalized configuration.
"""

import asyncio
import json
import logging
import os
import sys
import time
import traceback
import argparse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, Awaitable, TypeVar, Generic
from typing_extensions import TypedDict, Protocol

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
    from aiohttp import web, web_request, web_response
    from aiohttp.web import Application, Request, Response, StreamResponse
except ImportError as e:
    print(f"Error importing MCP modules: {e}")
    print("Please install MCP SDK: pip install mcp")
    sys.exit(1)

# Configuration imports
try:
    from config import load_config
    from config.schema import Config, LogLevel, TransportType
    CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Configuration system not available: {e}")
    print("Using default configuration")
    CONFIG_AVAILABLE = False

# Metrics imports
try:
    from metrics import MetricsCollector, MetricsStorage, MetricsExporter, MetricsDashboard, AlertManager
    from metrics.types import MetricsConfig
    METRICS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Metrics system not available: {e}")
    METRICS_AVAILABLE = False

# Docling imports with enhanced error handling and lazy loading
class DoclingImports:
    """
    Manages Docling imports with lazy loading and comprehensive error handling.
    Implements singleton pattern for efficient resource management.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._import_modules()
            DoclingImports._initialized = True
    
    def _import_modules(self):
        """Import Docling modules with comprehensive error handling and fallbacks."""
        self.DocumentConverter = None
        self.InputFormat = None
        self.PipelineOptions = None
        self.settings = None
        self.version = None
        self.available_features = set()
        self.import_errors = []
        
        # Declare global variable at the beginning of the method
        global DOCLING_AVAILABLE
        
        try:
            # Primary import with detailed error tracking
            import docling
            self.version = getattr(docling, '__version__', 'unknown')
            
            # Core converter import
            try:
                from docling.document_converter import DocumentConverter
                self.DocumentConverter = DocumentConverter
                self.available_features.add('converter')
            except ImportError as e:
                self.import_errors.append(f"DocumentConverter import failed: {e}")
            
            # Optional imports with feature detection
            optional_imports = {
                'InputFormat': 'docling.datamodel.base_models',
                'PipelineOptions': 'docling.datamodel.pipeline_options',
                'settings': 'docling.datamodel.settings',
                # Additional optional modules for future extensibility
                'Document': 'docling.datamodel.document_models',
                'Page': 'docling.datamodel.base_models',
                'Table': 'docling.datamodel.base_models'
            }
            
            for attr_name, module_path in optional_imports.items():
                try:
                    module = __import__(module_path, fromlist=[attr_name])
                    if hasattr(module, attr_name):
                        setattr(self, attr_name, getattr(module, attr_name))
                        self.available_features.add(attr_name.lower())
                except ImportError:
                    # Silently handle optional imports
                    pass
                except AttributeError:
                    # Module exists but attribute doesn't
                    pass
            
            # Set global availability flag
            DOCLING_AVAILABLE = self.DocumentConverter is not None
            
            # Use print for logging since logger might not be available yet
            if DOCLING_AVAILABLE:
                print(f"Docling v{self.version} loaded successfully with features: {sorted(self.available_features)}")
            else:
                print("Warning: Docling core components not available")
                
        except ImportError as e:
            self.import_errors.append(f"Docling package import failed: {e}")
            DOCLING_AVAILABLE = False
            print(f"Error: Docling not available: {e}")
    
    def is_available(self) -> bool:
        """Check if Docling core functionality is available."""
        return self.DocumentConverter is not None
    
    def has_feature(self, feature: str) -> bool:
        """Check if a specific feature is available."""
        return feature.lower() in self.available_features
    
    def get_converter(self, **kwargs):
        """Get a DocumentConverter instance with optional configuration."""
        if not self.is_available():
            raise ImportError("Docling DocumentConverter is not available")
        
        try:
            # Apply configuration if available
            if self.PipelineOptions and kwargs:
                pipeline_options = self.PipelineOptions(**kwargs)
                return self.DocumentConverter(pipeline_options=pipeline_options)
            else:
                return self.DocumentConverter()
        except Exception as e:
            logger.error(f"Failed to create DocumentConverter: {e}")
            raise
    
    def get_import_summary(self) -> dict:
        """Get a summary of import status and available features."""
        return {
            'available': self.is_available(),
            'version': self.version,
            'features': sorted(self.available_features),
            'errors': self.import_errors
        }

# Initialize Docling imports with lazy loading
_docling_imports = None

def get_docling_imports() -> DoclingImports:
    """Get the singleton DoclingImports instance."""
    global _docling_imports
    if _docling_imports is None:
        _docling_imports = DoclingImports()
    return _docling_imports

# Initialize imports immediately to set DOCLING_AVAILABLE flag
get_docling_imports()

# Type definitions for better code clarity
T = TypeVar('T')
HandlerFunction = Callable[..., Awaitable[Any]]
StreamType = Any  # MCP stream type (not directly accessible from imports)

# Global logger variable
logger: logging.Logger = logging.getLogger(__name__)

class DoclingMCPServer:
    """Docling MCP Server with official implementation patterns and configuration."""
    
    def __init__(self, config: Config) -> None:
        """Initialize server with configuration."""
        self.config = config
        self.server: Server = Server(config.server.name)
        self.capabilities: Optional[Any] = None
        
        # Initialize logger first to avoid undefined logger errors
        self.setup_logging()
        
        # Get logger after setup
        global logger
        logger = logging.getLogger(self.config.logging.name)
        
        # Initialize metrics system
        self.metrics_collector: Optional[MetricsCollector] = None
        self.metrics_storage: Optional[MetricsStorage] = None
        self.metrics_exporter: Optional[MetricsExporter] = None
        self.metrics_dashboard: Optional[MetricsDashboard] = None
        self.alert_manager: Optional[AlertManager] = None
        
        self.setup_handlers()
        self.setup_metrics()
        
        logger.info(f"Docling MCP Server '{config.server.name}' initialized")
    
    def setup_metrics(self) -> None:
        """Setup metrics collection system."""
        if not METRICS_AVAILABLE or not self.config.metrics.enabled:
            logger.info("Metrics collection is disabled")
            return
        
        try:
            # Initialize metrics collector
            self.metrics_collector = MetricsCollector(self.config.metrics)
            self.metrics_collector.start()
            
            # Initialize metrics storage
            self.metrics_storage = MetricsStorage(self.config.metrics)
            
            # Initialize metrics exporter (for Prometheus)
            self.metrics_exporter = MetricsExporter(self.config.metrics, self.metrics_collector)
            
            # Initialize metrics dashboard
            self.metrics_dashboard = MetricsDashboard(self.config.metrics, self.metrics_collector)
            
            # Initialize alert manager
            self.alert_manager = AlertManager(self.config.metrics, self.metrics_collector)
            self.alert_manager.start()
            
            # Add log alert handler
            from metrics.alerts import log_alert_handler
            self.alert_manager.add_alert_handler(log_alert_handler)
            
            logger.info("Metrics system initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing metrics system: {e}")
            # Continue without metrics if initialization fails
            self.metrics_collector = None
            self.metrics_storage = None
            self.metrics_exporter = None
            self.metrics_dashboard = None
            self.alert_manager = None
    
    def setup_logging(self) -> None:
        """Setup logging based on configuration."""
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config.logging.level.value))
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Create formatter
        formatter = logging.Formatter(self.config.logging.format)
        
        # Create handler based on output configuration
        if self.config.logging.output == 'stdout':
            handler = logging.StreamHandler(sys.stdout)
        elif self.config.logging.output == 'stderr':
            handler = logging.StreamHandler(sys.stderr)
        else:
            # File output
            log_file = Path(self.config.logging.output)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(self.config.logging.output)
        
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        
        # Set specific logger level
        global logger
        logger = logging.getLogger(self.config.logging.name)
        logger.setLevel(getattr(logging, self.config.logging.level.value))
    
    def setup_handlers(self) -> None:
        """Setup MCP server handlers following official patterns."""
        
        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            """List available document processing tools - official pattern."""
            tools: List[Tool] = []
            
            if DOCLING_AVAILABLE:
                tools.append(Tool(
                    name="convert_document",
                    description="Convert documents to structured format using Docling",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the document file"
                            },
                            "output_format": {
                                "type": "string",
                                "description": "Output format (markdown, text, json)",
                                "enum": ["markdown", "text", "json"],
                                "default": "markdown"
                            }
                        },
                        "required": ["file_path"],
                        "additionalProperties": False
                    }
                ))
                
                tools.append(Tool(
                    name="process_documents_batch",
                    description="Process multiple documents in batch",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_paths": {
                                "type": "array",
                                "description": "List of document file paths",
                                "items": {"type": "string"}
                            },
                            "output_format": {
                                "type": "string",
                                "description": "Output format for all documents",
                                "enum": ["markdown", "text", "json"],
                                "default": "markdown"
                            }
                        },
                        "required": ["file_paths"],
                        "additionalProperties": False
                    }
                ))
            
            tools.append(Tool(
                name="health_check",
                description="Check server health and capabilities",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            ))
            
            tools.append(Tool(
                name="get_config",
                description="Get current server configuration (sanitized)",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            ))
            
            return ListToolsResult(tools=tools)
        
        @self.server.call_tool()
        async def call_tool(name: Optional[str], arguments: Optional[Dict[str, Any]]) -> CallToolResult:
            """Handle tool calls with comprehensive error handling - official pattern."""
            start_time = time.time()
            timeout_occurred = False
            
            try:
                # Record request start
                if self.metrics_collector:
                    request_start = self.metrics_collector.record_request_start()
                
                # Validate tool name
                if not name:
                    if self.metrics_collector:
                        self.metrics_collector.record_request_end(request_start, success=False)
                    return CallToolResult(
                        content=[TextContent(type="text", text="Error: Tool name is required")],
                        isError=True
                    )
                
                # Execute tool with timeout per configuration
                result = await asyncio.wait_for(
                    self.execute_tool(name, arguments or {}),
                    timeout=self.config.performance.tool_timeout
                )
                
                # Record successful request
                if self.metrics_collector:
                    execution_time = time.time() - start_time
                    self.metrics_collector.record_request_end(request_start, success=True)
                    self.metrics_collector.record_tool_call(name, execution_time, success=True)
                
                return result
                
            except asyncio.TimeoutError:
                timeout_occurred = True
                if self.metrics_collector:
                    execution_time = time.time() - start_time
                    self.metrics_collector.record_request_end(request_start, success=False, timeout=True)
                    self.metrics_collector.record_tool_call(name, execution_time, success=False, timeout=True)
                
                return CallToolResult(
                    content=[TextContent(type="text", text="Error: Tool execution timed out")],
                    isError=True
                )
            except Exception as e:
                if self.metrics_collector:
                    execution_time = time.time() - start_time
                    self.metrics_collector.record_request_end(request_start, success=False)
                    self.metrics_collector.record_tool_call(name, execution_time, success=False)
                    self.metrics_collector.record_error("error")
                
                logger.error(f"Tool execution error: {e}", exc_info=True)
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")],
                    isError=True
                )
    
    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """Execute specific tool with proper error handling."""
        logger.info(f"Executing tool: {name} with arguments: {arguments}")
        
        if name == "health_check":
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Docling MCP Server is healthy. Docling available: {DOCLING_AVAILABLE}"
                )]
            )
        
        if name == "get_config":
            # Return sanitized configuration
            config_dict = self.config.to_dict()
            # Remove sensitive information
            if 'security' in config_dict:
                config_dict['security'] = {k: v for k, v in config_dict['security'].items() 
                                         if k not in ['api_keys', 'secrets']}
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Server Configuration:\n{json.dumps(config_dict, indent=2)}"
                )]
            )
        
        if not DOCLING_AVAILABLE:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="Error: Docling is not available. Please install docling: pip install docling"
                )],
                isError=True
            )
        
        if name == "convert_document":
            return await self.convert_document(arguments)
        elif name == "process_documents_batch":
            return await self.process_documents_batch(arguments)
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True
            )
    
    def validate_file_size(self, file_path: str) -> Optional[str]:
        """Validate file size against configuration limits."""
        try:
            file_size = os.path.getsize(file_path)
            if file_size > self.config.docling.max_file_size:
                return f"File size ({file_size} bytes) exceeds maximum allowed size ({self.config.docling.max_file_size} bytes)"
        except OSError as e:
            return f"Cannot access file: {e}"
        return None
    
    async def convert_document(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Convert a single document using Docling."""
        file_path: Optional[str] = arguments.get("file_path")
        output_format: str = arguments.get("output_format", "markdown")
        
        if not file_path:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: file_path is required")],
                isError=True
            )
        
        if not os.path.exists(file_path):
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: File not found: {file_path}")],
                isError=True
            )
        
        # Validate file size
        size_error = self.validate_file_size(file_path)
        if size_error:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: {size_error}")],
                isError=True
            )
        
        try:
            # Configure Docling with cache settings
            if self.config.docling.enable_cache:
                os.environ['DOCLING_CACHE_DIR'] = self.config.docling.cache_dir
            
            # Get converter with enhanced configuration
            docling_imports = get_docling_imports()
            converter = docling_imports.get_converter()
            result: Any = converter.convert(file_path)
            
            content: str
            if output_format == "markdown":
                content = result.document.export_to_markdown()
            elif output_format == "text":
                content = result.document.export_to_text()
            elif output_format == "json":
                content = json.dumps(result.document.export_to_dict(), indent=2)
            else:
                content = result.document.export_to_markdown()
            
            return CallToolResult(
                content=[TextContent(type="text", text=content)]
            )
            
        except Exception as e:
            logger.error(f"Document conversion error: {e}", exc_info=True)
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error converting document: {str(e)}")],
                isError=True
            )
    
    async def process_documents_batch(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Process multiple documents in batch."""
        file_paths: List[str] = arguments.get("file_paths", [])
        output_format: str = arguments.get("output_format", "markdown")
        
        if not file_paths:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: file_paths is required")],
                isError=True
            )
        
        results: List[str] = []
        errors: List[str] = []
        
        for file_path in file_paths:
            if not os.path.exists(file_path):
                errors.append(f"File not found: {file_path}")
                continue
            
            # Validate file size
            size_error = self.validate_file_size(file_path)
            if size_error:
                errors.append(f"Error processing {file_path}: {size_error}")
                continue
            
            try:
                # Configure Docling with cache settings
                if self.config.docling.enable_cache:
                    os.environ['DOCLING_CACHE_DIR'] = self.config.docling.cache_dir
                
                # Get converter with enhanced configuration
                docling_imports = get_docling_imports()
                converter = docling_imports.get_converter()
                result: Any = converter.convert(file_path)
                
                content: str
                if output_format == "markdown":
                    content = result.document.export_to_markdown()
                elif output_format == "text":
                    content = result.document.export_to_text()
                elif output_format == "json":
                    content = json.dumps(result.document.export_to_dict(), indent=2)
                else:
                    content = result.document.export_to_markdown()
                
                results.append(f"=== {file_path} ===\n{content}")
                
            except Exception as e:
                errors.append(f"Error processing {file_path}: {str(e)}")
        
        output: List[str] = []
        if results:
            output.append("\n\n".join(results))
        if errors:
            output.append("Errors:\n" + "\n".join(errors))
        
        return CallToolResult(
            content=[TextContent(type="text", text="\n\n".join(output) if output else "No results")]
        )

def create_custom_sse_handler(config: Config, sse_transport: Any, server: DoclingMCPServer) -> Callable[[Request], Awaitable[StreamResponse]]:
    """Create a custom SSE handler for MCP SDK compatibility when official methods are missing."""
    
    async def custom_sse_handler(request: Request) -> StreamResponse:
        """Custom SSE handler that implements the official MCP SSE protocol."""
        connection_id = f"{request.remote}_{id(request)}"
        logger.info(f"SSE connection from {request.remote}")
        
        # Record connection start
        if server.metrics_collector:
            server.metrics_collector.record_connection_start(connection_id)
        
        # Prepare SSE response
        response: StreamResponse = web.StreamResponse()
        
        # Configure CORS headers
        cors_headers = {}
        if config.security.enable_cors:
            cors_headers.update({
                'Access-Control-Allow-Origin': ', '.join(config.sse.cors_origins) if config.sse.cors_origins != ['*'] else '*',
                'Access-Control-Allow-Methods': ', '.join(config.sse.cors_methods),
                'Access-Control-Allow-Headers': ', '.join(config.sse.cors_headers),
                'Access-Control-Max-Age': str(config.sse.cors_max_age),
            })
        
        response.headers.update({
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            **cors_headers
        })
        
        await response.prepare(request)
        
        try:
            # Create custom streams for MCP communication
            from asyncio import Queue
            from mcp.server.session import ServerSession
            
            # Create queues for bidirectional communication
            client_to_server_queue: asyncio.Queue[Any] = Queue()
            server_to_client_queue: asyncio.Queue[Any] = Queue()
            
            # Create stream objects that mimic the MCP stream interface
            class SimpleStream:
                def __init__(self, input_queue: asyncio.Queue[Any], output_queue: asyncio.Queue[Any]) -> None:
                    self.input_queue: asyncio.Queue[Any] = input_queue
                    self.output_queue: asyncio.Queue[Any] = output_queue
                
                async def read(self) -> Any:
                    return await self.input_queue.get()
                
                async def write(self, data: Any) -> None:
                    await self.output_queue.put(data)
            
            # Create the streams
            read_stream: SimpleStream = SimpleStream(client_to_server_queue, server_to_client_queue)
            write_stream: SimpleStream = SimpleStream(server_to_client_queue, client_to_server_queue)
            
            # Start the MCP server session in the background
            session_task: asyncio.Task[Any] = asyncio.create_task(
                server.server.run(
                    read_stream,
                    write_stream,
                    server.server.create_initialization_options()
                )
            )
            
            # Handle SSE events
            while True:
                try:
                    # Check for data to send to client
                    if not server_to_client_queue.empty():
                        data: Any = await server_to_client_queue.get()
                        # Format as SSE event
                        sse_data: str = f"data: {json.dumps(data)}\n\n"
                        await response.write(sse_data.encode('utf-8'))
                        
                        # Record SSE event sent
                        if server.metrics_collector:
                            server.metrics_collector.record_sse_event_sent(len(sse_data))
                    
                    # Send keepalive based on configuration
                    await asyncio.sleep(config.sse.keepalive_interval)
                    
                    # Record keepalive sent
                    if server.metrics_collector:
                        server.metrics_collector.record_keepalive_sent()
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"SSE handling error: {e}")
                    if server.metrics_collector:
                        server.metrics_collector.record_sse_error()
                    break
            
            # Clean up
            session_task.cancel()
            try:
                await session_task
            except asyncio.CancelledError:
                pass
            
        except Exception as e:
            logger.error(f"SSE error: {e}")
            if server.metrics_collector:
                server.metrics_collector.record_connection_error()
                server.metrics_collector.record_sse_error()
            error_event: str = f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
            await response.write(error_event.encode('utf-8'))
        finally:
            logger.info(f"SSE connection from {request.remote} closed")
            if server.metrics_collector:
                server.metrics_collector.record_connection_end(connection_id)
                server.metrics_collector.record_client_disconnect()
            await response.write_eof()
        
        return response
    
    return custom_sse_handler

async def run_stdio_server(server: DoclingMCPServer) -> None:
    """Official STDIO transport implementation following official pattern."""
    logger.info("Starting Docling MCP Server with STDIO transport...")
    
    try:
        # Use context manager for proper cleanup - official pattern
        async with stdio_server() as (read_stream, write_stream):
            # Run server with initialization options
            await server.server.run(
                read_stream,
                write_stream,
                server.server.create_initialization_options()
            )
    except BrokenPipeError:
        logger.info("STDIO connection closed")
    except KeyboardInterrupt:
        logger.info("Server interrupted")
    except Exception as e:
        logger.error(f"STDIO server error: {e}")
        logger.error(traceback.format_exc())
        raise

async def run_http_server(server: DoclingMCPServer) -> None:
    """Official HTTP transport implementation with SSE following official pattern."""
    config = server.config
    logger.info(f"Starting Docling MCP Server with HTTP transport on {config.server.host}:{config.server.port}...")
    
    try:
        # Create aiohttp application
        app: Application = web.Application()
        
        # Create SSE transport with proper configuration - official pattern
        sse_transport: SseServerTransport = SseServerTransport(config.sse.endpoint)
        
        # Handle MCP sessions - official pattern
        async def handle_session(session_streams: tuple[Any, Any]) -> None:
            """Handle MCP sessions with proper error handling and logging."""
            read_stream, write_stream = session_streams
            try:
                await server.server.run(
                    read_stream,
                    write_stream,
                    server.server.create_initialization_options()
                )
            except Exception as e:
                logger.error(f"Session handling error: {e}", exc_info=True)
                raise
        
        # Set up session handler for SSE transport - official pattern
        sse_transport.handle_session = handle_session
        
        # Add SSE endpoint using the correct method - official pattern
        try:
            # Try the official method name first
            app.router.add_get(config.sse.endpoint, sse_transport.handle_request)
        except AttributeError:
            # Fallback to alternative method names or custom implementation
            logger.warning("SseServerTransport.handle_request not found, trying alternative methods")
            
            # Check for alternative method names
            if hasattr(sse_transport, 'handle_sse_request'):
                app.router.add_get(config.sse.endpoint, sse_transport.handle_sse_request)
            elif hasattr(sse_transport, 'sse_handler'):
                app.router.add_get(config.sse.endpoint, sse_transport.sse_handler)
            elif hasattr(sse_transport, 'handle'):
                app.router.add_get(config.sse.endpoint, sse_transport.handle)
            else:
                # If none of the expected methods exist, implement custom SSE handler
                logger.info("Implementing custom SSE handler for MCP SDK compatibility")
                app.router.add_get(config.sse.endpoint, create_custom_sse_handler(config, sse_transport, server))
        
        # Add health check endpoint with metrics
        async def health_check(request: Request) -> Response:
            """Health check endpoint for monitoring with metrics integration."""
            try:
                # Get current metrics for health status
                health_status = "healthy"
                status_code = 200
                
                if server.alert_manager:
                    alert_health = server.alert_manager.get_health_status()
                    if alert_health['status'] != 'healthy':
                        health_status = alert_health['status']
                        status_code = 503 if alert_health['status'] in ['critical', 'emergency'] else 200
                
                # Record health check
                if server.metrics_collector:
                    server.metrics_collector.record_health_check(health_status, failure=(status_code != 200))
                
                # Return enhanced health response
                response_data = {
                    "status": health_status,
                    "timestamp": datetime.now().isoformat(),
                    "docling_available": DOCLING_AVAILABLE,
                    "metrics_available": METRICS_AVAILABLE and server.metrics_collector is not None,
                    "uptime_seconds": server.metrics_collector.get_system_metrics().uptime_seconds if server.metrics_collector else 0
                }
                
                return web.Response(
                    text=json.dumps(response_data, indent=2),
                    content_type="application/json",
                    status=status_code
                )
                
            except Exception as e:
                logger.error(f"Health check error: {e}")
                return web.Response(text="Service Unavailable", status=503)
        
        app.router.add_get(config.health_check.endpoint, health_check)
        
        # Configure CORS for browser clients - official pattern
        if config.security.enable_cors:
            async def handle_cors_options(request: Request) -> Response:
                """Handle CORS preflight requests."""
                return web.Response(
                    headers={
                        "Access-Control-Allow-Origin": ', '.join(config.sse.cors_origins) if config.sse.cors_origins != ['*'] else '*',
                        "Access-Control-Allow-Methods": ', '.join(config.sse.cors_methods),
                        "Access-Control-Allow-Headers": ', '.join(config.sse.cors_headers),
                        "Access-Control-Max-Age": str(config.sse.cors_max_age),
                    }
                )
            
            app.router.add_options(config.sse.endpoint, handle_cors_options)
        
        # Setup metrics endpoints if available
        if server.metrics_exporter:
            server.metrics_exporter.setup_routes(app)
            logger.info(f"Metrics endpoints configured on port {config.server.port}")
        
        if server.metrics_dashboard:
            server.metrics_dashboard.setup_routes(app)
            logger.info(f"Dashboard endpoint configured on port {config.server.port}")
        
        # Start server with proper session handling
        runner: web.AppRunner = web.AppRunner(app)
        await runner.setup()
        site: web.TCPSite = web.TCPSite(runner, config.server.host, config.server.port)
        await site.start()
        
        logger.info(f"HTTP server started on {config.server.host}:{config.server.port}")
        logger.info(f"SSE endpoint available at http://{config.server.host}:{config.server.port}{config.sse.endpoint}")
        logger.info(f"Health check available at http://{config.server.host}:{config.server.port}{config.health_check.endpoint}")
        
        # Keep server running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        finally:
            await runner.cleanup()
        
    except Exception as e:
        logger.error(f"Error running HTTP server: {e}")
        logger.error(traceback.format_exc())
        raise

def main() -> None:
    """Main entry point with configuration support."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description="Docling MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        help="Transport type to use (overrides configuration)"
    )
    parser.add_argument(
        "--host",
        help="Host for HTTP transport (overrides configuration)"
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Port for HTTP transport (overrides configuration)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (overrides configuration)"
    )
    parser.add_argument(
        "--config-file",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--environment",
        choices=["default", "development", "production"],
        default="default",
        help="Environment to use for configuration"
    )
    parser.add_argument(
        "--create-config",
        action="store_true",
        help="Create default configuration files and exit"
    )
    
    args: argparse.Namespace = parser.parse_args()
    
    # Create configuration files if requested
    if args.create_config:
        try:
            from config.loader import ConfigLoader
            loader = ConfigLoader()
            loader.create_default_config()
            loader.create_environment_templates()
            print("Configuration files created successfully!")
            print(f"Default config: {loader.config_dir}/default.yaml")
            print(f"Development config: {loader.config_dir}/development.yaml")
            print(f"Production config: {loader.config_dir}/production.yaml")
            sys.exit(0)
        except Exception as e:
            print(f"Error creating configuration files: {e}")
            sys.exit(1)
    
    # Load configuration
    try:
        if CONFIG_AVAILABLE:
            config = load_config(
                environment=args.environment,
                config_file=args.config_file
            )
            # Initialize logger after config is loaded
            server = DoclingMCPServer(config)
            logger.info(f"Loaded configuration for environment: {args.environment}")
        else:
            # Fallback to default configuration
            from config.schema import Config
            config = Config()
            # Initialize logger after config is loaded
            server = DoclingMCPServer(config)
            logger.warning("Using default configuration (config system not available)")
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)
    
    # Apply command line overrides
    if args.transport:
        config.server.transport = TransportType(args.transport)
    if args.host:
        config.server.host = args.host
    if args.port:
        config.server.port = args.port
    if args.log_level:
        config.logging.level = LogLevel(args.log_level)
    
    # Create server with configuration
    server: DoclingMCPServer = DoclingMCPServer(config)
    
    # Run with appropriate transport
    try:
        if config.server.transport == TransportType.STDIO:
            asyncio.run(run_stdio_server(server))
        elif config.server.transport == TransportType.HTTP:
            asyncio.run(run_http_server(server))
        else:
            logger.error(f"Unknown transport: {config.server.transport}")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()