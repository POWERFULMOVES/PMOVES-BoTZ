"""
Metrics Exporter - Provides Prometheus-compatible metrics endpoint and other export formats.
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from aiohttp import web, web_response
import json

from .types import MetricsSnapshot, MetricsConfig
from .collector import MetricsCollector

logger = logging.getLogger(__name__)


class MetricsExporter:
    """Handles metrics export in various formats including Prometheus."""
    
    def __init__(self, config: MetricsConfig, collector: MetricsCollector):
        """Initialize metrics exporter."""
        self.config = config
        self.collector = collector
        self.enabled = config.prometheus_enabled
        
        # Prometheus metrics cache
        self._prometheus_metrics_cache: str = ""
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = 10  # seconds
        
        logger.info("MetricsExporter initialized")
    
    def get_prometheus_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        if not self.enabled:
            return ""
        
        try:
            # Check cache
            if (self._cache_timestamp and 
                (datetime.now() - self._cache_timestamp).total_seconds() < self._cache_ttl):
                return self._prometheus_metrics_cache
            
            # Get current metrics
            snapshot = self.collector.get_current_metrics()
            if not snapshot:
                return ""
            
            # Generate Prometheus format
            metrics_text = self._generate_prometheus_metrics(snapshot)
            
            # Update cache
            self._prometheus_metrics_cache = metrics_text
            self._cache_timestamp = datetime.now()
            
            return metrics_text
            
        except Exception as e:
            logger.error(f"Error generating Prometheus metrics: {e}")
            return ""
    
    def _generate_prometheus_metrics(self, snapshot: MetricsSnapshot) -> str:
        """Generate Prometheus-formatted metrics text."""
        lines = []
        
        # Add header
        lines.append("# Docling MCP Server Metrics")
        lines.append(f"# Generated at {snapshot.timestamp.isoformat()}")
        lines.append("")
        
        # Connection metrics
        lines.extend(self._format_connection_metrics(snapshot.connection_metrics))
        lines.append("")
        
        # Request metrics
        lines.extend(self._format_request_metrics(snapshot.request_metrics))
        lines.append("")
        
        # Resource metrics
        lines.extend(self._format_resource_metrics(snapshot.resource_metrics))
        lines.append("")
        
        # SSE metrics
        lines.extend(self._format_sse_metrics(snapshot.sse_metrics))
        lines.append("")
        
        # Tool metrics
        lines.extend(self._format_tool_metrics(snapshot.tool_metrics))
        lines.append("")
        
        # System metrics
        lines.extend(self._format_system_metrics(snapshot.system_metrics))
        
        return "\n".join(lines)
    
    def _format_connection_metrics(self, metrics) -> List[str]:
        """Format connection metrics for Prometheus."""
        return [
            "# HELP docling_mcp_active_connections Number of active connections",
            "# TYPE docling_mcp_active_connections gauge",
            f"docling_mcp_active_connections {metrics.active_connections}",
            "",
            "# HELP docling_mcp_total_connections_total Total number of connections",
            "# TYPE docling_mcp_total_connections_total counter",
            f"docling_mcp_total_connections_total {metrics.total_connections}",
            "",
            "# HELP docling_mcp_connection_duration_seconds Connection duration statistics",
            "# TYPE docling_mcp_connection_duration_seconds summary",
            f"docling_mcp_connection_duration_seconds{{quantile=\"0.5\"}} {metrics.connection_duration_avg}",
            f"docling_mcp_connection_duration_seconds{{quantile=\"1.0\"}} {metrics.connection_duration_max}",
            "",
            "# HELP docling_mcp_connection_errors_total Total connection errors",
            "# TYPE docling_mcp_connection_errors_total counter",
            f"docling_mcp_connection_errors_total {metrics.connection_errors}",
            "",
            "# HELP docling_mcp_connection_success_rate Connection success rate percentage",
            "# TYPE docling_mcp_connection_success_rate gauge",
            f"docling_mcp_connection_success_rate {metrics.connection_success_rate}"
        ]
    
    def _format_request_metrics(self, metrics) -> List[str]:
        """Format request metrics for Prometheus."""
        return [
            "# HELP docling_mcp_requests_total Total number of requests",
            "# TYPE docling_mcp_requests_total counter",
            f"docling_mcp_requests_total {metrics.request_count}",
            "",
            "# HELP docling_mcp_request_rate Requests per second",
            "# TYPE docling_mcp_request_rate gauge",
            f"docling_mcp_request_rate {metrics.request_rate}",
            "",
            "# HELP docling_mcp_response_time_seconds Response time statistics",
            "# TYPE docling_mcp_response_time_seconds summary",
            f"docling_mcp_response_time_seconds{{quantile=\"0.5\"}} {metrics.response_time_p50}",
            f"docling_mcp_response_time_seconds{{quantile=\"0.95\"}} {metrics.response_time_p95}",
            f"docling_mcp_response_time_seconds{{quantile=\"0.99\"}} {metrics.response_time_p99}",
            f"docling_mcp_response_time_seconds{{quantile=\"1.0\"}} {metrics.response_time_max}",
            "",
            "# HELP docling_mcp_success_rate Request success rate percentage",
            "# TYPE docling_mcp_success_rate gauge",
            f"docling_mcp_success_rate {metrics.success_rate}",
            "",
            "# HELP docling_mcp_error_rate Error rate percentage",
            "# TYPE docling_mcp_error_rate gauge",
            f"docling_mcp_error_rate {metrics.error_rate}",
            "",
            "# HELP docling_mcp_throughput_bytes_per_second Request throughput",
            "# TYPE docling_mcp_throughput_bytes_per_second gauge",
            f"docling_mcp_throughput_bytes_per_second {metrics.throughput}"
        ]
    
    def _format_resource_metrics(self, metrics) -> List[str]:
        """Format resource metrics for Prometheus."""
        return [
            "# HELP docling_mcp_cpu_usage_percent CPU usage percentage",
            "# TYPE docling_mcp_cpu_usage_percent gauge",
            f"docling_mcp_cpu_usage_percent {metrics.cpu_usage_percent}",
            "",
            "# HELP docling_mcp_memory_usage_bytes Memory usage in bytes",
            "# TYPE docling_mcp_memory_usage_bytes gauge",
            f"docling_mcp_memory_usage_bytes {metrics.memory_usage_bytes}",
            "",
            "# HELP docling_mcp_memory_usage_percent Memory usage percentage",
            "# TYPE docling_mcp_memory_usage_percent gauge",
            f"docling_mcp_memory_usage_percent {metrics.memory_usage_percent}",
            "",
            "# HELP docling_mcp_disk_usage_bytes Disk usage in bytes",
            "# TYPE docling_mcp_disk_usage_bytes gauge",
            f"docling_mcp_disk_usage_bytes {metrics.disk_usage_bytes}",
            "",
            "# HELP docling_mcp_disk_usage_percent Disk usage percentage",
            "# TYPE docling_mcp_disk_usage_percent gauge",
            f"docling_mcp_disk_usage_percent {metrics.disk_usage_percent}",
            "",
            "# HELP docling_mcp_network_bytes_total Network traffic",
            "# TYPE docling_mcp_network_bytes_total counter",
            f"docling_mcp_network_bytes_total{{direction=\"in\"}} {metrics.network_in_bytes}",
            f"docling_mcp_network_bytes_total{{direction=\"out\"}} {metrics.network_out_bytes}",
            "",
            "# HELP docling_mcp_network_rate_bytes_per_second Network rate",
            "# TYPE docling_mcp_network_rate_bytes_per_second gauge",
            f"docling_mcp_network_rate_bytes_per_second{{direction=\"in\"}} {metrics.network_in_rate}",
            f"docling_mcp_network_rate_bytes_per_second{{direction=\"out\"}} {metrics.network_out_rate}",
            "",
            "# HELP docling_mcp_open_file_descriptors Open file descriptors",
            "# TYPE docling_mcp_open_file_descriptors gauge",
            f"docling_mcp_open_file_descriptors {metrics.open_file_descriptors}",
            "",
            "# HELP docling_mcp_thread_count Number of threads",
            "# TYPE docling_mcp_thread_count gauge",
            f"docling_mcp_thread_count {metrics.thread_count}"
        ]
    
    def _format_sse_metrics(self, metrics) -> List[str]:
        """Format SSE metrics for Prometheus."""
        return [
            "# HELP docling_mcp_sse_events_sent_total Total SSE events sent",
            "# TYPE docling_mcp_sse_events_sent_total counter",
            f"docling_mcp_sse_events_sent_total {metrics.events_sent}",
            "",
            "# HELP docling_mcp_sse_events_received_total Total SSE events received",
            "# TYPE docling_mcp_sse_events_received_total counter",
            f"docling_mcp_sse_events_received_total {metrics.events_received}",
            "",
            "# HELP docling_mcp_sse_event_processing_time_seconds SSE event processing time",
            "# TYPE docling_mcp_sse_event_processing_time_seconds summary",
            f"docling_mcp_sse_event_processing_time_seconds{{quantile=\"0.5\"}} {metrics.event_processing_time_avg}",
            f"docling_mcp_sse_event_processing_time_seconds{{quantile=\"1.0\"}} {metrics.event_processing_time_max}",
            "",
            "# HELP docling_mcp_sse_stream_latency_seconds SSE stream latency",
            "# TYPE docling_mcp_sse_stream_latency_seconds gauge",
            f"docling_mcp_sse_stream_latency_seconds {metrics.stream_latency_avg}",
            "",
            "# HELP docling_mcp_sse_errors_total Total SSE errors",
            "# TYPE docling_mcp_sse_errors_total counter",
            f"docling_mcp_sse_errors_total {metrics.stream_errors}",
            "",
            "# HELP docling_mcp_sse_keepalive_sent_total Total keepalive messages sent",
            "# TYPE docling_mcp_sse_keepalive_sent_total counter",
            f"docling_mcp_sse_keepalive_sent_total {metrics.keepalive_sent}",
            "",
            "# HELP docling_mcp_sse_client_disconnects_total Total client disconnects",
            "# TYPE docling_mcp_sse_client_disconnects_total counter",
            f"docling_mcp_sse_client_disconnects_total {metrics.client_disconnects}"
        ]
    
    def _format_tool_metrics(self, metrics) -> List[str]:
        """Format tool metrics for Prometheus."""
        lines = [
            "# HELP docling_mcp_tool_calls_total Total tool calls",
            "# TYPE docling_mcp_tool_calls_total counter",
            f"docling_mcp_tool_calls_total {metrics.tool_calls_total}",
            "",
            "# HELP docling_mcp_tool_calls_success_total Successful tool calls",
            "# TYPE docling_mcp_tool_calls_success_total counter",
            f"docling_mcp_tool_calls_success_total {metrics.tool_calls_success}",
            "",
            "# HELP docling_mcp_tool_calls_error_total Failed tool calls",
            "# TYPE docling_mcp_tool_calls_error_total counter",
            f"docling_mcp_tool_calls_error_total {metrics.tool_calls_error}",
            "",
            "# HELP docling_mcp_tool_calls_timeout_total Timed out tool calls",
            "# TYPE docling_mcp_tool_calls_timeout_total counter",
            f"docling_mcp_tool_calls_timeout_total {metrics.tool_calls_timeout}",
            "",
            "# HELP docling_mcp_tool_execution_time_seconds Tool execution time statistics",
            "# TYPE docling_mcp_tool_execution_time_seconds summary",
            f"docling_mcp_tool_execution_time_seconds{{quantile=\"0.5\"}} {metrics.tool_execution_time_p50}",
            f"docling_mcp_tool_execution_time_seconds{{quantile=\"0.95\"}} {metrics.tool_execution_time_p95}",
            f"docling_mcp_tool_execution_time_seconds{{quantile=\"0.99\"}} {metrics.tool_execution_time_p99}",
            f"docling_mcp_tool_execution_time_seconds{{quantile=\"1.0\"}} {metrics.tool_execution_time_max}",
            ""
        ]
        
        # Add per-tool metrics
        if metrics.tool_calls_by_name:
            lines.extend([
                "# HELP docling_mcp_tool_calls_by_name Tool calls by name",
                "# TYPE docling_mcp_tool_calls_by_name counter"
            ])
            for tool_name, count in metrics.tool_calls_by_name.items():
                lines.append(f'docling_mcp_tool_calls_by_name{{tool_name="{tool_name}"}} {count}')
            
            lines.append("")
        
        if metrics.tool_errors_by_name:
            lines.extend([
                "# HELP docling_mcp_tool_errors_by_name Tool errors by name",
                "# TYPE docling_mcp_tool_errors_by_name counter"
            ])
            for tool_name, count in metrics.tool_errors_by_name.items():
                lines.append(f'docling_mcp_tool_errors_by_name{{tool_name="{tool_name}"}} {count}')
            
            lines.append("")
        
        if metrics.tool_timeout_by_name:
            lines.extend([
                "# HELP docling_mcp_tool_timeouts_by_name Tool timeouts by name",
                "# TYPE docling_mcp_tool_timeouts_by_name counter"
            ])
            for tool_name, count in metrics.tool_timeout_by_name.items():
                lines.append(f'docling_mcp_tool_timeouts_by_name{{tool_name="{tool_name}"}} {count}')
        
        return lines
    
    def _format_system_metrics(self, metrics) -> List[str]:
        """Format system metrics for Prometheus."""
        return [
            "# HELP docling_mcp_uptime_seconds Service uptime in seconds",
            "# TYPE docling_mcp_uptime_seconds gauge",
            f"docling_mcp_uptime_seconds {metrics.uptime_seconds}",
            "",
            "# HELP docling_mcp_health_check_failures_total Total health check failures",
            "# TYPE docling_mcp_health_check_failures_total counter",
            f"docling_mcp_health_check_failures_total {metrics.health_check_failures}",
            "",
            "# HELP docling_mcp_errors_total Total errors",
            "# TYPE docling_mcp_errors_total counter",
            f"docling_mcp_errors_total {metrics.error_count_total}",
            "",
            "# HELP docling_mcp_warnings_total Total warnings",
            "# TYPE docling_mcp_warnings_total counter",
            f"docling_mcp_warnings_total {metrics.warning_count_total}",
            "",
            "# HELP docling_mcp_service_status Service status (1=running, 0=stopped)",
            "# TYPE docling_mcp_service_status gauge",
            f"docling_mcp_service_status {1 if metrics.service_status == 'running' else 0}"
        ]
    
    def get_json_metrics(self) -> Dict[str, Any]:
        """Get metrics in JSON format."""
        try:
            snapshot = self.collector.get_current_metrics()
            if not snapshot:
                return {}
            
            return self.collector.get_all_metrics()
            
        except Exception as e:
            logger.error(f"Error generating JSON metrics: {e}")
            return {}
    
    def get_csv_metrics(self) -> str:
        """Get metrics in CSV format."""
        try:
            snapshot = self.collector.get_current_metrics()
            if not snapshot:
                return ""
            
            # Create CSV with current metrics
            import io
            import csv
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Headers
            writer.writerow([
                'timestamp', 'active_connections', 'total_connections',
                'request_count', 'request_rate', 'response_time_avg',
                'cpu_usage_percent', 'memory_usage_percent',
                'events_sent', 'events_received', 'tool_calls_total',
                'uptime_seconds', 'error_count_total'
            ])
            
            # Data row
            writer.writerow([
                snapshot.timestamp.isoformat(),
                snapshot.connection_metrics.active_connections,
                snapshot.connection_metrics.total_connections,
                snapshot.request_metrics.request_count,
                snapshot.request_metrics.request_rate,
                snapshot.request_metrics.response_time_avg,
                snapshot.resource_metrics.cpu_usage_percent,
                snapshot.resource_metrics.memory_usage_percent,
                snapshot.sse_metrics.events_sent,
                snapshot.sse_metrics.events_received,
                snapshot.tool_metrics.tool_calls_total,
                snapshot.system_metrics.uptime_seconds,
                snapshot.system_metrics.error_count_total
            ])
            
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating CSV metrics: {e}")
            return ""
    
    async def handle_prometheus_request(self, request: web.Request) -> web.Response:
        """Handle Prometheus metrics HTTP request."""
        try:
            metrics_text = self.get_prometheus_metrics()
            
            if not metrics_text:
                return web.Response(
                    text="# No metrics available\n",
                    content_type="text/plain; version=0.0.4; charset=utf-8",
                    status=503
                )
            
            return web.Response(
                text=metrics_text,
                content_type="text/plain; version=0.0.4; charset=utf-8",
                status=200
            )
            
        except Exception as e:
            logger.error(f"Error handling Prometheus request: {e}")
            return web.Response(
                text=f"# Error: {str(e)}\n",
                content_type="text/plain; version=0.0.4; charset=utf-8",
                status=500
            )
    
    async def handle_json_request(self, request: web.Request) -> web.Response:
        """Handle JSON metrics HTTP request."""
        try:
            metrics_data = self.get_json_metrics()
            
            if not metrics_data:
                return web.Response(
                    text=json.dumps({"error": "No metrics available"}),
                    content_type="application/json",
                    status=503
                )
            
            return web.Response(
                text=json.dumps(metrics_data, indent=2),
                content_type="application/json",
                status=200
            )
            
        except Exception as e:
            logger.error(f"Error handling JSON request: {e}")
            return web.Response(
                text=json.dumps({"error": str(e)}),
                content_type="application/json",
                status=500
            )
    
    async def handle_csv_request(self, request: web.Request) -> web.Response:
        """Handle CSV metrics HTTP request."""
        try:
            csv_data = self.get_csv_metrics()
            
            if not csv_data:
                return web.Response(
                    text="No metrics available",
                    content_type="text/plain",
                    status=503
                )
            
            return web.Response(
                text=csv_data,
                content_type="text/csv",
                status=200,
                headers={
                    "Content-Disposition": "attachment; filename=\"docling_mcp_metrics.csv\""
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling CSV request: {e}")
            return web.Response(
                text=f"Error: {str(e)}",
                content_type="text/plain",
                status=500
            )
    
    def setup_routes(self, app: web.Application) -> None:
        """Setup HTTP routes for metrics endpoints."""
        if not self.enabled:
            return
        
        # Prometheus metrics endpoint
        app.router.add_get(self.config.prometheus_endpoint, self.handle_prometheus_request)
        
        # JSON metrics endpoint
        app.router.add_get(f"{self.config.prometheus_endpoint}/json", self.handle_json_request)
        
        # CSV metrics endpoint
        app.router.add_get(f"{self.config.prometheus_endpoint}/csv", self.handle_csv_request)
        
        logger.info(f"Metrics endpoints configured:")
        logger.info(f"  Prometheus: {self.config.prometheus_endpoint}")
        logger.info(f"  JSON: {self.config.prometheus_endpoint}/json")
        logger.info(f"  CSV: {self.config.prometheus_endpoint}/csv")