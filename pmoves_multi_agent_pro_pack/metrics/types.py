"""
Type definitions for performance metrics collection system.
"""

from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field
from datetime import datetime
import enum


class MetricType(enum.Enum):
    """Types of metrics that can be collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertSeverity(enum.Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class MetricValue:
    """Represents a single metric value."""
    name: str
    value: Union[int, float]
    metric_type: MetricType
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    unit: str = ""
    description: str = ""


@dataclass
class ConnectionMetrics:
    """Connection-related metrics."""
    active_connections: int = 0
    total_connections: int = 0
    connection_duration_avg: float = 0.0
    connection_duration_max: float = 0.0
    connection_duration_min: float = 0.0
    connection_errors: int = 0
    connection_success_rate: float = 100.0
    connection_queue_size: int = 0
    rejected_connections: int = 0


@dataclass
class RequestMetrics:
    """Request/response metrics."""
    request_count: int = 0
    request_rate: float = 0.0  # requests per second
    response_time_avg: float = 0.0
    response_time_p50: float = 0.0  # 50th percentile
    response_time_p95: float = 0.0  # 95th percentile
    response_time_p99: float = 0.0  # 99th percentile
    response_time_max: float = 0.0
    response_time_min: float = 0.0
    success_rate: float = 100.0
    error_rate: float = 0.0
    timeout_rate: float = 0.0
    throughput: float = 0.0  # bytes per second


@dataclass
class ResourceMetrics:
    """System resource usage metrics."""
    cpu_usage_percent: float = 0.0
    memory_usage_bytes: int = 0
    memory_usage_percent: float = 0.0
    disk_usage_bytes: int = 0
    disk_usage_percent: float = 0.0
    network_in_bytes: int = 0
    network_out_bytes: int = 0
    network_in_rate: float = 0.0  # bytes per second
    network_out_rate: float = 0.0  # bytes per second
    open_file_descriptors: int = 0
    thread_count: int = 0
    process_count: int = 0


@dataclass
class SSEMetrics:
    """Server-Sent Events specific metrics."""
    events_sent: int = 0
    events_received: int = 0
    event_queue_size: int = 0
    event_processing_time_avg: float = 0.0
    event_processing_time_max: float = 0.0
    event_processing_time_min: float = 0.0
    stream_latency_avg: float = 0.0
    stream_latency_max: float = 0.0
    stream_errors: int = 0
    keepalive_sent: int = 0
    client_disconnects: int = 0


@dataclass
class ToolMetrics:
    """Tool execution metrics."""
    tool_calls_total: int = 0
    tool_calls_success: int = 0
    tool_calls_error: int = 0
    tool_calls_timeout: int = 0
    tool_execution_time_avg: float = 0.0
    tool_execution_time_p50: float = 0.0
    tool_execution_time_p95: float = 0.0
    tool_execution_time_p99: float = 0.0
    tool_execution_time_max: float = 0.0
    tool_execution_time_min: float = 0.0
    tool_calls_by_name: Dict[str, int] = field(default_factory=dict)
    tool_errors_by_name: Dict[str, int] = field(default_factory=dict)
    tool_timeout_by_name: Dict[str, int] = field(default_factory=dict)


@dataclass
class SystemMetrics:
    """Overall system health and uptime metrics."""
    uptime_seconds: float = 0.0
    start_time: Optional[datetime] = None
    health_check_status: str = "healthy"
    health_check_failures: int = 0
    last_health_check: Optional[datetime] = None
    service_status: str = "running"
    restart_count: int = 0
    error_count_total: int = 0
    warning_count_total: int = 0


@dataclass
class PerformanceAlert:
    """Represents a performance alert."""
    alert_id: str
    severity: AlertSeverity
    metric_name: str
    current_value: Union[int, float]
    threshold_value: Union[int, float]
    message: str
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    acknowledged: bool = False
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class MetricsSnapshot:
    """Complete snapshot of all metrics at a point in time."""
    timestamp: datetime
    connection_metrics: ConnectionMetrics
    request_metrics: RequestMetrics
    resource_metrics: ResourceMetrics
    sse_metrics: SSEMetrics
    tool_metrics: ToolMetrics
    system_metrics: SystemMetrics
    custom_metrics: Dict[str, MetricValue] = field(default_factory=dict)


@dataclass
class MetricsConfig:
    """Configuration for metrics collection."""
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