"""
Metrics Collector - Core performance metrics collection system.
"""

import asyncio
import time
import psutil
import os
import threading
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics
import logging

from .types import (
    MetricType, MetricValue, ConnectionMetrics, RequestMetrics, 
    ResourceMetrics, SSEMetrics, ToolMetrics, SystemMetrics,
    MetricsSnapshot, MetricsConfig
)

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Core metrics collection system for Docling MCP Server."""
    
    def __init__(self, config: MetricsConfig):
        """Initialize the metrics collector."""
        self.config = config
        self.enabled = config.enabled
        
        # Metrics storage
        self._metrics_history: deque = deque(maxlen=10000)  # Keep last 10k snapshots
        self._current_metrics: Optional[MetricsSnapshot] = None
        
        # Connection tracking
        self._active_connections: Dict[str, float] = {}  # connection_id -> start_time
        self._connection_durations: deque = deque(maxlen=1000)
        self._connection_errors = 0
        self._total_connections = 0
        
        # Request tracking
        self._request_times: deque = deque(maxlen=10000)
        self._request_count = 0
        self._request_errors = 0
        self._request_timeouts = 0
        self._bytes_processed = 0
        
        # Resource tracking
        self._process = psutil.Process(os.getpid())
        self._last_resource_check = time.time()
        self._last_network_stats = self._get_network_stats()
        
        # SSE tracking
        self._sse_events_sent = 0
        self._sse_events_received = 0
        self._sse_event_times: deque = deque(maxlen=1000)
        self._sse_stream_latencies: deque = deque(maxlen=1000)
        self._sse_errors = 0
        self._keepalive_sent = 0
        self._client_disconnects = 0
        
        # Tool tracking
        self._tool_calls: Dict[str, int] = defaultdict(int)
        self._tool_errors: Dict[str, int] = defaultdict(int)
        self._tool_timeouts: Dict[str, int] = defaultdict(int)
        self._tool_execution_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # System tracking
        self._start_time = datetime.now()
        self._health_check_failures = 0
        self._total_errors = 0
        self._total_warnings = 0
        
        # Background collection task
        self._collection_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info("MetricsCollector initialized")
    
    def start(self) -> None:
        """Start the metrics collection system."""
        if not self.enabled:
            logger.info("Metrics collection is disabled")
            return
            
        self._running = True
        # Create background collection task
        if asyncio.get_event_loop().is_running():
            self._collection_task = asyncio.create_task(self._collection_loop())
        logger.info("Metrics collection started")
    
    def stop(self) -> None:
        """Stop the metrics collection system."""
        self._running = False
        if self._collection_task:
            self._collection_task.cancel()
        logger.info("Metrics collection stopped")
    
    async def _collection_loop(self) -> None:
        """Background loop for periodic metrics collection."""
        try:
            while self._running:
                await self._collect_system_metrics()
                await asyncio.sleep(self.config.collection_interval)
        except asyncio.CancelledError:
            logger.info("Metrics collection loop cancelled")
        except Exception as e:
            logger.error(f"Error in metrics collection loop: {e}")
    
    async def _collect_system_metrics(self) -> None:
        """Collect system-level metrics."""
        try:
            # Create current snapshot
            snapshot = MetricsSnapshot(
                timestamp=datetime.now(),
                connection_metrics=self.get_connection_metrics(),
                request_metrics=self.get_request_metrics(),
                resource_metrics=self.get_resource_metrics(),
                sse_metrics=self.get_sse_metrics(),
                tool_metrics=self.get_tool_metrics(),
                system_metrics=self.get_system_metrics()
            )
            
            # Store snapshot
            with self._lock:
                self._current_metrics = snapshot
                self._metrics_history.append(snapshot)
                
                # Clean up old snapshots based on retention
                retention_delta = timedelta(hours=self.config.retention_hours)
                cutoff_time = datetime.now() - retention_delta
                
                while (self._metrics_history and 
                       self._metrics_history[0].timestamp < cutoff_time):
                    self._metrics_history.popleft()
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    # Connection Metrics
    def record_connection_start(self, connection_id: str) -> None:
        """Record the start of a new connection."""
        if not self.enabled:
            return
            
        with self._lock:
            self._active_connections[connection_id] = time.time()
            self._total_connections += 1
    
    def record_connection_end(self, connection_id: str, error: bool = False) -> None:
        """Record the end of a connection."""
        if not self.enabled:
            return
            
        with self._lock:
            if connection_id in self._active_connections:
                duration = time.time() - self._active_connections[connection_id]
                self._connection_durations.append(duration)
                del self._active_connections[connection_id]
                
                if error:
                    self._connection_errors += 1
    
    def record_connection_error(self) -> None:
        """Record a connection error."""
        if not self.enabled:
            return
            
        with self._lock:
            self._connection_errors += 1
    
    def get_connection_metrics(self) -> ConnectionMetrics:
        """Get current connection metrics."""
        with self._lock:
            durations = list(self._connection_durations)
            
            if durations:
                avg_duration = statistics.mean(durations)
                max_duration = max(durations)
                min_duration = min(durations)
            else:
                avg_duration = max_duration = min_duration = 0.0
            
            total_connections = self._total_connections
            error_rate = (self._connection_errors / total_connections * 100) if total_connections > 0 else 0.0
            
            return ConnectionMetrics(
                active_connections=len(self._active_connections),
                total_connections=total_connections,
                connection_duration_avg=avg_duration,
                connection_duration_max=max_duration,
                connection_duration_min=min_duration,
                connection_errors=self._connection_errors,
                connection_success_rate=100.0 - error_rate,
                connection_queue_size=0,  # Will be implemented if needed
                rejected_connections=0  # Will be implemented if needed
            )
    
    # Request Metrics
    def record_request_start(self) -> float:
        """Record the start of a request. Returns start time."""
        return time.time() if self.enabled else 0.0
    
    def record_request_end(self, start_time: float, success: bool = True, 
                          bytes_processed: int = 0, timeout: bool = False) -> None:
        """Record the end of a request."""
        if not self.enabled or start_time == 0.0:
            return
            
        duration = time.time() - start_time
        
        with self._lock:
            self._request_times.append(duration)
            self._request_count += 1
            self._bytes_processed += bytes_processed
            
            if not success:
                self._request_errors += 1
            if timeout:
                self._request_timeouts += 1
    
    def get_request_metrics(self) -> RequestMetrics:
        """Get current request metrics."""
        with self._lock:
            times = list(self._request_times)
            
            if not times:
                return RequestMetrics()
            
            # Calculate percentiles
            times_sorted = sorted(times)
            p50_idx = int(len(times_sorted) * 0.5)
            p95_idx = int(len(times_sorted) * 0.95)
            p99_idx = int(len(times_sorted) * 0.99)
            
            # Calculate rates (requests per second over last minute)
            current_time = time.time()
            recent_requests = sum(1 for t in times if current_time - t < 60)
            request_rate = recent_requests / 60.0
            
            # Calculate throughput (bytes per second)
            throughput = self._bytes_processed / (time.time() - self._start_time.timestamp()) if self._start_time else 0.0
            
            total_requests = self._request_count
            error_rate = (self._request_errors / total_requests * 100) if total_requests > 0 else 0.0
            timeout_rate = (self._request_timeouts / total_requests * 100) if total_requests > 0 else 0.0
            
            return RequestMetrics(
                request_count=total_requests,
                request_rate=request_rate,
                response_time_avg=statistics.mean(times),
                response_time_p50=times_sorted[p50_idx] if p50_idx < len(times_sorted) else 0.0,
                response_time_p95=times_sorted[p95_idx] if p95_idx < len(times_sorted) else 0.0,
                response_time_p99=times_sorted[p99_idx] if p99_idx < len(times_sorted) else 0.0,
                response_time_max=max(times),
                response_time_min=min(times),
                success_rate=100.0 - error_rate,
                error_rate=error_rate,
                timeout_rate=timeout_rate,
                throughput=throughput
            )
    
    # Resource Metrics
    def _get_network_stats(self) -> Dict[str, int]:
        """Get current network statistics."""
        try:
            net_io = psutil.net_io_counters()
            return {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv
            }
        except Exception:
            return {'bytes_sent': 0, 'bytes_recv': 0}
    
    def get_resource_metrics(self) -> ResourceMetrics:
        """Get current resource usage metrics."""
        try:
            # CPU usage
            cpu_percent = self._process.cpu_percent(interval=0.1)
            
            # Memory usage
            memory_info = self._process.memory_info()
            memory_percent = self._process.memory_percent()
            
            # Disk usage
            disk_usage = psutil.disk_usage('/')
            
            # Network usage
            current_net_stats = self._get_network_stats()
            current_time = time.time()
            time_delta = current_time - self._last_resource_check
            
            if time_delta > 0 and self._last_network_stats:
                bytes_sent_rate = (current_net_stats['bytes_sent'] - self._last_network_stats['bytes_sent']) / time_delta
                bytes_recv_rate = (current_net_stats['bytes_recv'] - self._last_network_stats['bytes_recv']) / time_delta
            else:
                bytes_sent_rate = bytes_recv_rate = 0.0
            
            self._last_network_stats = current_net_stats
            self._last_resource_check = current_time
            
            # Process info
            open_files = len(self._process.open_files())
            threads = self._process.num_threads()
            
            return ResourceMetrics(
                cpu_usage_percent=cpu_percent,
                memory_usage_bytes=memory_info.rss,
                memory_usage_percent=memory_percent,
                disk_usage_bytes=disk_usage.used,
                disk_usage_percent=(disk_usage.used / disk_usage.total * 100) if disk_usage.total > 0 else 0.0,
                network_in_bytes=current_net_stats['bytes_recv'],
                network_out_bytes=current_net_stats['bytes_sent'],
                network_in_rate=bytes_recv_rate,
                network_out_rate=bytes_sent_rate,
                open_file_descriptors=open_files,
                thread_count=threads,
                process_count=1  # This process
            )
            
        except Exception as e:
            logger.error(f"Error collecting resource metrics: {e}")
            return ResourceMetrics()
    
    # SSE Metrics
    def record_sse_event_sent(self, event_size: int = 0) -> None:
        """Record an SSE event being sent."""
        if not self.enabled:
            return
            
        with self._lock:
            self._sse_events_sent += 1
    
    def record_sse_event_received(self, processing_time: float = 0.0) -> None:
        """Record an SSE event being received."""
        if not self.enabled:
            return
            
        with self._lock:
            self._sse_events_received += 1
            if processing_time > 0:
                self._sse_event_times.append(processing_time)
    
    def record_sse_stream_latency(self, latency: float) -> None:
        """Record SSE stream latency."""
        if not self.enabled:
            return
            
        with self._lock:
            self._sse_stream_latencies.append(latency)
    
    def record_sse_error(self) -> None:
        """Record an SSE error."""
        if not self.enabled:
            return
            
        with self._lock:
            self._sse_errors += 1
    
    def record_keepalive_sent(self) -> None:
        """Record a keepalive message being sent."""
        if not self.enabled:
            return
            
        with self._lock:
            self._keepalive_sent += 1
    
    def record_client_disconnect(self) -> None:
        """Record a client disconnect."""
        if not self.enabled:
            return
            
        with self._lock:
            self._client_disconnects += 1
    
    def get_sse_metrics(self) -> SSEMetrics:
        """Get current SSE metrics."""
        with self._lock:
            event_times = list(self._sse_event_times)
            stream_latencies = list(self._sse_stream_latencies)
            
            if event_times:
                event_avg = statistics.mean(event_times)
                event_max = max(event_times)
                event_min = min(event_times)
            else:
                event_avg = event_max = event_min = 0.0
            
            if stream_latencies:
                latency_avg = statistics.mean(stream_latencies)
                latency_max = max(stream_latencies)
            else:
                latency_avg = latency_max = 0.0
            
            return SSEMetrics(
                events_sent=self._sse_events_sent,
                events_received=self._sse_events_received,
                event_queue_size=0,  # Will be implemented if queue tracking is added
                event_processing_time_avg=event_avg,
                event_processing_time_max=event_max,
                event_processing_time_min=event_min,
                stream_latency_avg=latency_avg,
                stream_latency_max=latency_max,
                stream_errors=self._sse_errors,
                keepalive_sent=self._keepalive_sent,
                client_disconnects=self._client_disconnects
            )
    
    # Tool Metrics
    def record_tool_call(self, tool_name: str, execution_time: float, 
                        success: bool = True, timeout: bool = False) -> None:
        """Record a tool call execution."""
        if not self.enabled:
            return
            
        with self._lock:
            self._tool_calls[tool_name] += 1
            self._tool_execution_times[tool_name].append(execution_time)
            
            if not success:
                self._tool_errors[tool_name] += 1
            if timeout:
                self._tool_timeouts[tool_name] += 1
    
    def get_tool_metrics(self) -> ToolMetrics:
        """Get current tool metrics."""
        with self._lock:
            total_calls = sum(self._tool_calls.values())
            total_success = total_calls - sum(self._tool_errors.values())
            total_errors = sum(self._tool_errors.values())
            total_timeouts = sum(self._tool_timeouts.values())
            
            # Calculate execution time statistics across all tools
            all_execution_times = []
            for times in self._tool_execution_times.values():
                all_execution_times.extend(times)
            
            if all_execution_times:
                execution_times_sorted = sorted(all_execution_times)
                p50_idx = int(len(execution_times_sorted) * 0.5)
                p95_idx = int(len(execution_times_sorted) * 0.95)
                p99_idx = int(len(execution_times_sorted) * 0.99)
                
                avg_time = statistics.mean(all_execution_times)
                p50_time = execution_times_sorted[p50_idx] if p50_idx < len(execution_times_sorted) else 0.0
                p95_time = execution_times_sorted[p95_idx] if p95_idx < len(execution_times_sorted) else 0.0
                p99_time = execution_times_sorted[p99_idx] if p99_idx < len(execution_times_sorted) else 0.0
                max_time = max(all_execution_times)
                min_time = min(all_execution_times)
            else:
                avg_time = p50_time = p95_time = p99_time = max_time = min_time = 0.0
            
            return ToolMetrics(
                tool_calls_total=total_calls,
                tool_calls_success=total_success,
                tool_calls_error=total_errors,
                tool_calls_timeout=total_timeouts,
                tool_execution_time_avg=avg_time,
                tool_execution_time_p50=p50_time,
                tool_execution_time_p95=p95_time,
                tool_execution_time_p99=p99_time,
                tool_execution_time_max=max_time,
                tool_execution_time_min=min_time,
                tool_calls_by_name=dict(self._tool_calls),
                tool_errors_by_name=dict(self._tool_errors),
                tool_timeout_by_name=dict(self._tool_timeouts)
            )
    
    # System Metrics
    def record_health_check(self, status: str, failure: bool = False) -> None:
        """Record a health check result."""
        if not self.enabled:
            return
            
        with self._lock:
            if failure:
                self._health_check_failures += 1
    
    def record_error(self, severity: str = "error") -> None:
        """Record an error occurrence."""
        if not self.enabled:
            return
            
        with self._lock:
            if severity == "error":
                self._total_errors += 1
            elif severity == "warning":
                self._total_warnings += 1
    
    def get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics."""
        with self._lock:
            uptime = (datetime.now() - self._start_time).total_seconds() if self._start_time else 0.0
            
            return SystemMetrics(
                uptime_seconds=uptime,
                start_time=self._start_time,
                health_check_status="healthy" if self._health_check_failures == 0 else "unhealthy",
                health_check_failures=self._health_check_failures,
                last_health_check=datetime.now(),
                service_status="running" if self._running else "stopped",
                restart_count=0,  # Will be implemented if restart tracking is added
                error_count_total=self._total_errors,
                warning_count_total=self._total_warnings
            )
    
    # General Methods
    def get_current_metrics(self) -> Optional[MetricsSnapshot]:
        """Get the most recent metrics snapshot."""
        with self._lock:
            return self._current_metrics
    
    def get_metrics_history(self, hours: int = 1) -> List[MetricsSnapshot]:
        """Get metrics history for the specified number of hours."""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            return [snapshot for snapshot in self._metrics_history 
                   if snapshot.timestamp >= cutoff_time]
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metrics as a dictionary."""
        current = self.get_current_metrics()
        if not current:
            return {}
        
        return {
            'timestamp': current.timestamp.isoformat(),
            'connection_metrics': current.connection_metrics.__dict__,
            'request_metrics': current.request_metrics.__dict__,
            'resource_metrics': current.resource_metrics.__dict__,
            'sse_metrics': current.sse_metrics.__dict__,
            'tool_metrics': current.tool_metrics.__dict__,
            'system_metrics': current.system_metrics.__dict__
        }
    
    def reset_metrics(self) -> None:
        """Reset all metrics counters."""
        with self._lock:
            # Reset counters but keep configuration
            self._active_connections.clear()
            self._connection_durations.clear()
            self._connection_errors = 0
            self._total_connections = 0
            
            self._request_times.clear()
            self._request_count = 0
            self._request_errors = 0
            self._request_timeouts = 0
            self._bytes_processed = 0
            
            self._sse_events_sent = 0
            self._sse_events_received = 0
            self._sse_event_times.clear()
            self._sse_stream_latencies.clear()
            self._sse_errors = 0
            self._keepalive_sent = 0
            self._client_disconnects = 0
            
            self._tool_calls.clear()
            self._tool_errors.clear()
            self._tool_timeouts.clear()
            for times in self._tool_execution_times.values():
                times.clear()
            
            self._health_check_failures = 0
            self._total_errors = 0
            self._total_warnings = 0
            
            logger.info("All metrics have been reset")