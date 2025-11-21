"""
Configuration schema for Docling MCP Server.

This module defines the configuration schema and validation logic.
"""

from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
import enum


class LogLevel(enum.Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class TransportType(enum.Enum):
    """Transport types."""
    STDIO = "stdio"
    HTTP = "http"


class OutputFormat(enum.Enum):
    """Document output formats."""
    MARKDOWN = "markdown"
    TEXT = "text"
    JSON = "json"


@dataclass
class ServerConfig:
    """Server configuration."""
    host: str = "0.0.0.0"
    port: int = 3020
    transport: TransportType = TransportType.STDIO
    name: str = "docling-mcp"


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: LogLevel = LogLevel.INFO
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    name: str = "docling-mcp"
    output: str = "stdout"  # stdout, stderr, or file path


@dataclass
class SSEConfig:
    """Server-Sent Events configuration."""
    endpoint: str = "/mcp"
    keepalive_interval: float = 0.1  # seconds
    connection_timeout: float = 30.0  # seconds
    max_queue_size: int = 1000
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    cors_methods: List[str] = field(default_factory=lambda: ["GET", "OPTIONS"])
    cors_headers: List[str] = field(default_factory=lambda: ["Content-Type", "Accept", "Cache-Control"])
    cors_max_age: int = 86400  # 24 hours


@dataclass
class PerformanceConfig:
    """Performance configuration."""
    tool_timeout: float = 30.0  # seconds
    max_connections: int = 100
    rate_limit_requests: int = 1000
    rate_limit_window: int = 3600  # seconds


@dataclass
class SecurityConfig:
    """Security configuration."""
    enable_cors: bool = True
    allowed_origins: List[str] = field(default_factory=lambda: ["*"])
    enable_rate_limiting: bool = False
    max_request_size: int = 10 * 1024 * 1024  # 10MB


@dataclass
class DoclingConfig:
    """Docling integration configuration."""
    cache_dir: str = "/data/cache"
    enable_cache: bool = True
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    supported_formats: List[str] = field(default_factory=lambda: [
        "pdf", "docx", "pptx", "xlsx", "html", "txt", "md"
    ])
    pipeline_options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheckConfig:
    """Health check configuration."""
    endpoint: str = "/health"
    interval: int = 30  # seconds
    timeout: int = 10  # seconds
    retries: int = 3
    start_period: int = 30  # seconds


@dataclass
class MetricsConfig:
    """Metrics and monitoring configuration."""
    enabled: bool = True
    collection_interval: float = 10.0  # seconds
    retention_hours: int = 24
    storage_backend: str = "memory"  # memory, file, database
    storage_path: str = "/data/metrics"
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    prometheus_endpoint: str = "/metrics"
    dashboard_enabled: bool = True
    dashboard_port: int = 8080
    dashboard_endpoint: str = "/dashboard"
    alerting_enabled: bool = True
    alert_thresholds: Dict[str, Dict[str, Union[int, float]]] = field(default_factory=lambda: {
        "cpu_usage_percent": {"warning": 70.0, "critical": 85.0},
        "memory_usage_percent": {"warning": 80.0, "critical": 90.0},
        "response_time_p95": {"warning": 1000.0, "critical": 2000.0},  # milliseconds
        "error_rate": {"warning": 5.0, "critical": 10.0},  # percentage
        "connection_errors": {"warning": 10, "critical": 50},
        "tool_timeout_rate": {"warning": 2.0, "critical": 5.0}  # percentage
    })
    export_formats: List[str] = field(default_factory=lambda: ["json", "csv"])
    export_interval: int = 300  # seconds (5 minutes)
    compression_enabled: bool = True
    compression_threshold: int = 1000  # number of data points


@dataclass
class Config:
    """Main configuration class."""
    server: ServerConfig = field(default_factory=ServerConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    sse: SSEConfig = field(default_factory=SSEConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    docling: DoclingConfig = field(default_factory=DoclingConfig)
    health_check: HealthCheckConfig = field(default_factory=HealthCheckConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create configuration from dictionary."""
        config = cls()
        
        # Server configuration
        if 'server' in data:
            server_data = data['server']
            config.server = ServerConfig(
                host=server_data.get('host', config.server.host),
                port=server_data.get('port', config.server.port),
                transport=TransportType(server_data.get('transport', config.server.transport.value)),
                name=server_data.get('name', config.server.name)
            )
        
        # Logging configuration
        if 'logging' in data:
            logging_data = data['logging']
            config.logging = LoggingConfig(
                level=LogLevel(logging_data.get('level', config.logging.level.value)),
                format=logging_data.get('format', config.logging.format),
                name=logging_data.get('name', config.logging.name),
                output=logging_data.get('output', config.logging.output)
            )
        
        # SSE configuration
        if 'sse' in data:
            sse_data = data['sse']
            config.sse = SSEConfig(
                endpoint=sse_data.get('endpoint', config.sse.endpoint),
                keepalive_interval=sse_data.get('keepalive_interval', config.sse.keepalive_interval),
                connection_timeout=sse_data.get('connection_timeout', config.sse.connection_timeout),
                max_queue_size=sse_data.get('max_queue_size', config.sse.max_queue_size),
                cors_origins=sse_data.get('cors_origins', config.sse.cors_origins),
                cors_methods=sse_data.get('cors_methods', config.sse.cors_methods),
                cors_headers=sse_data.get('cors_headers', config.sse.cors_headers),
                cors_max_age=sse_data.get('cors_max_age', config.sse.cors_max_age)
            )
        
        # Performance configuration
        if 'performance' in data:
            perf_data = data['performance']
            config.performance = PerformanceConfig(
                tool_timeout=perf_data.get('tool_timeout', config.performance.tool_timeout),
                max_connections=perf_data.get('max_connections', config.performance.max_connections),
                rate_limit_requests=perf_data.get('rate_limit_requests', config.performance.rate_limit_requests),
                rate_limit_window=perf_data.get('rate_limit_window', config.performance.rate_limit_window)
            )
        
        # Security configuration
        if 'security' in data:
            security_data = data['security']
            config.security = SecurityConfig(
                enable_cors=security_data.get('enable_cors', config.security.enable_cors),
                allowed_origins=security_data.get('allowed_origins', config.security.allowed_origins),
                enable_rate_limiting=security_data.get('enable_rate_limiting', config.security.enable_rate_limiting),
                max_request_size=security_data.get('max_request_size', config.security.max_request_size)
            )
        
        # Docling configuration
        if 'docling' in data:
            docling_data = data['docling']
            config.docling = DoclingConfig(
                cache_dir=docling_data.get('cache_dir', config.docling.cache_dir),
                enable_cache=docling_data.get('enable_cache', config.docling.enable_cache),
                max_file_size=docling_data.get('max_file_size', config.docling.max_file_size),
                supported_formats=docling_data.get('supported_formats', config.docling.supported_formats),
                pipeline_options=docling_data.get('pipeline_options', config.docling.pipeline_options)
            )
        
        # Health check configuration
        if 'health_check' in data:
            health_data = data['health_check']
            config.health_check = HealthCheckConfig(
                endpoint=health_data.get('endpoint', config.health_check.endpoint),
                interval=health_data.get('interval', config.health_check.interval),
                timeout=health_data.get('timeout', config.health_check.timeout),
                retries=health_data.get('retries', config.health_check.retries),
                start_period=health_data.get('start_period', config.health_check.start_period)
            )
        
        # Metrics configuration
        if 'metrics' in data:
            metrics_data = data['metrics']
            config.metrics = MetricsConfig(
                enabled=metrics_data.get('enabled', config.metrics.enabled),
                collection_interval=metrics_data.get('collection_interval', config.metrics.collection_interval),
                retention_hours=metrics_data.get('retention_hours', config.metrics.retention_hours),
                storage_backend=metrics_data.get('storage_backend', config.metrics.storage_backend),
                storage_path=metrics_data.get('storage_path', config.metrics.storage_path),
                prometheus_enabled=metrics_data.get('prometheus_enabled', config.metrics.prometheus_enabled),
                prometheus_port=metrics_data.get('prometheus_port', config.metrics.prometheus_port),
                prometheus_endpoint=metrics_data.get('prometheus_endpoint', config.metrics.prometheus_endpoint),
                dashboard_enabled=metrics_data.get('dashboard_enabled', config.metrics.dashboard_enabled),
                dashboard_port=metrics_data.get('dashboard_port', config.metrics.dashboard_port),
                dashboard_endpoint=metrics_data.get('dashboard_endpoint', config.metrics.dashboard_endpoint),
                alerting_enabled=metrics_data.get('alerting_enabled', config.metrics.alerting_enabled),
                alert_thresholds=metrics_data.get('alert_thresholds', config.metrics.alert_thresholds),
                export_formats=metrics_data.get('export_formats', config.metrics.export_formats),
                export_interval=metrics_data.get('export_interval', config.metrics.export_interval),
                compression_enabled=metrics_data.get('compression_enabled', config.metrics.compression_enabled),
                compression_threshold=metrics_data.get('compression_threshold', config.metrics.compression_threshold)
            )
        
        return config

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'server': {
                'host': self.server.host,
                'port': self.server.port,
                'transport': self.server.transport.value,
                'name': self.server.name
            },
            'logging': {
                'level': self.logging.level.value,
                'format': self.logging.format,
                'name': self.logging.name,
                'output': self.logging.output
            },
            'sse': {
                'endpoint': self.sse.endpoint,
                'keepalive_interval': self.sse.keepalive_interval,
                'connection_timeout': self.sse.connection_timeout,
                'max_queue_size': self.sse.max_queue_size,
                'cors_origins': self.sse.cors_origins,
                'cors_methods': self.sse.cors_methods,
                'cors_headers': self.sse.cors_headers,
                'cors_max_age': self.sse.cors_max_age
            },
            'performance': {
                'tool_timeout': self.performance.tool_timeout,
                'max_connections': self.performance.max_connections,
                'rate_limit_requests': self.performance.rate_limit_requests,
                'rate_limit_window': self.performance.rate_limit_window
            },
            'security': {
                'enable_cors': self.security.enable_cors,
                'allowed_origins': self.security.allowed_origins,
                'enable_rate_limiting': self.security.enable_rate_limiting,
                'max_request_size': self.security.max_request_size
            },
            'docling': {
                'cache_dir': self.docling.cache_dir,
                'enable_cache': self.docling.enable_cache,
                'max_file_size': self.docling.max_file_size,
                'supported_formats': self.docling.supported_formats,
                'pipeline_options': self.docling.pipeline_options
            },
            'health_check': {
                'endpoint': self.health_check.endpoint,
                'interval': self.health_check.interval,
                'timeout': self.health_check.timeout,
                'retries': self.health_check.retries,
                'start_period': self.health_check.start_period
            },
            'metrics': {
                'enabled': self.metrics.enabled,
                'collection_interval': self.metrics.collection_interval,
                'retention_hours': self.metrics.retention_hours,
                'storage_backend': self.metrics.storage_backend,
                'storage_path': self.metrics.storage_path,
                'prometheus_enabled': self.metrics.prometheus_enabled,
                'prometheus_port': self.metrics.prometheus_port,
                'prometheus_endpoint': self.metrics.prometheus_endpoint,
                'dashboard_enabled': self.metrics.dashboard_enabled,
                'dashboard_port': self.metrics.dashboard_port,
                'dashboard_endpoint': self.metrics.dashboard_endpoint,
                'alerting_enabled': self.metrics.alerting_enabled,
                'alert_thresholds': self.metrics.alert_thresholds,
                'export_formats': self.metrics.export_formats,
                'export_interval': self.metrics.export_interval,
                'compression_enabled': self.metrics.compression_enabled,
                'compression_threshold': self.metrics.compression_threshold
            }
        }


def validate_config(config: Config) -> List[str]:
    """Validate configuration and return list of errors."""
    errors = []
    
    # Server validation
    if not isinstance(config.server.port, int) or not (1 <= config.server.port <= 65535):
        errors.append("Server port must be an integer between 1 and 65535")
    
    if not config.server.host:
        errors.append("Server host cannot be empty")
    
    # Performance validation
    if config.performance.tool_timeout <= 0:
        errors.append("Tool timeout must be positive")
    
    if config.performance.max_connections <= 0:
        errors.append("Max connections must be positive")
    
    # Security validation
    if config.security.max_request_size <= 0:
        errors.append("Max request size must be positive")
    
    # Docling validation
    if config.docling.max_file_size <= 0:
        errors.append("Max file size must be positive")
    
    if not config.docling.supported_formats:
        errors.append("Supported formats cannot be empty")
    
    # Health check validation
    if config.health_check.interval <= 0:
        errors.append("Health check interval must be positive")
    
    if config.health_check.timeout <= 0:
        errors.append("Health check timeout must be positive")
    
    if config.health_check.retries < 0:
        errors.append("Health check retries cannot be negative")
    
    # Metrics validation
    if config.metrics.collection_interval <= 0:
        errors.append("Metrics collection interval must be positive")
    
    if config.metrics.retention_hours <= 0:
        errors.append("Metrics retention hours must be positive")
    
    if config.metrics.prometheus_port < 1 or config.metrics.prometheus_port > 65535:
        errors.append("Prometheus port must be between 1 and 65535")
    
    if config.metrics.dashboard_port < 1 or config.metrics.dashboard_port > 65535:
        errors.append("Dashboard port must be between 1 and 65535")
    
    return errors