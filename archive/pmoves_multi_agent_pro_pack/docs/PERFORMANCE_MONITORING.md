# Performance Monitoring Guide for Docling MCP Server

This guide provides comprehensive documentation for the performance monitoring and metrics collection system implemented in the Docling MCP Server.

## Overview

The Docling MCP Server includes a comprehensive performance monitoring system that provides real-time insights into server performance, resource usage, and operational health. The system is designed for production observability with minimal performance overhead.

## Features

### Core Metrics Collection
- **Connection Metrics**: Active connections, total connections, connection duration, success rates
- **Request Metrics**: Request rate, response times (P50, P95, P99), success/error rates, throughput
- **Resource Metrics**: CPU usage, memory usage, disk usage, network I/O, file descriptors
- **SSE Handler Metrics**: Events sent/received, queue sizes, stream latency, keepalive tracking
- **Tool Execution Metrics**: Tool call counts, execution times, success/error rates, timeouts
- **System Health Metrics**: Uptime, health check results, error trends, restart counts

### Storage and Export
- **In-Memory Storage**: Fast access with configurable retention periods
- **File-Based Storage**: Persistent storage with compression and automatic cleanup
- **Multiple Export Formats**: JSON, CSV, Prometheus-compatible metrics
- **Configurable Retention**: Customizable data retention policies

### Real-Time Dashboard
- **Web-Based Interface**: Real-time metrics visualization
- **WebSocket Updates**: Live data streaming with automatic reconnection
- **Responsive Design**: Mobile-friendly interface
- **Key Performance Indicators**: At-a-glance performance overview

### Alerting System
- **Configurable Thresholds**: Custom alert thresholds for all metrics
- **Multiple Severity Levels**: Info, Warning, Critical, Emergency
- **Auto-Resolution**: Automatic alert resolution when conditions improve
- **Extensible Handlers**: Custom alert notification handlers

## Configuration

### Basic Configuration

Add the following to your configuration file:

```yaml
metrics:
  enabled: true
  collection_interval: 10.0  # seconds
  retention_hours: 24
  storage_backend: "memory"  # or "file" for persistence
  storage_path: "/data/metrics"
```

### Prometheus Integration

Enable Prometheus metrics endpoint:

```yaml
metrics:
  prometheus_enabled: true
  prometheus_port: 9090
  prometheus_endpoint: "/metrics"
```

### Dashboard Configuration

Enable the real-time dashboard:

```yaml
metrics:
  dashboard_enabled: true
  dashboard_port: 8080
  dashboard_endpoint: "/dashboard"
```

### Alerting Configuration

Configure performance thresholds:

```yaml
metrics:
  alerting_enabled: true
  alert_thresholds:
    cpu_usage_percent:
      warning: 70.0
      critical: 85.0
    memory_usage_percent:
      warning: 80.0
      critical: 90.0
    response_time_p95:
      warning: 1000.0  # milliseconds
      critical: 2000.0
    error_rate:
      warning: 5.0  # percentage
      critical: 10.0
```

## Usage

### Accessing Metrics

#### Prometheus Metrics Endpoint
```bash
curl http://localhost:3020/metrics
```

#### JSON Metrics Endpoint
```bash
curl http://localhost:3020/metrics/json
```

#### CSV Export
```bash
curl http://localhost:3020/metrics/csv
```

### Real-Time Dashboard
Open your browser and navigate to:
```
http://localhost:3020/dashboard
```

### Health Check with Metrics
```bash
curl http://localhost:3020/health
```

Returns enhanced health information including metrics status:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-09T17:30:00Z",
  "docling_available": true,
  "metrics_available": true,
  "uptime_seconds": 3600
}
```

## Metrics Reference

### Connection Metrics

| Metric | Description | Unit |
|--------|-------------|------|
| `active_connections` | Currently active connections | count |
| `total_connections` | Total connections since start | count |
| `connection_duration_avg` | Average connection duration | seconds |
| `connection_success_rate` | Connection success percentage | % |

### Request Metrics

| Metric | Description | Unit |
|--------|-------------|------|
| `request_count` | Total requests processed | count |
| `request_rate` | Requests per second | req/s |
| `response_time_avg` | Average response time | seconds |
| `response_time_p95` | 95th percentile response time | seconds |
| `success_rate` | Request success percentage | % |
| `error_rate` | Request error percentage | % |
| `throughput` | Data throughput | bytes/s |

### Resource Metrics

| Metric | Description | Unit |
|--------|-------------|------|
| `cpu_usage_percent` | CPU usage percentage | % |
| `memory_usage_bytes` | Memory usage in bytes | bytes |
| `memory_usage_percent` | Memory usage percentage | % |
| `disk_usage_bytes` | Disk usage in bytes | bytes |
| `disk_usage_percent` | Disk usage percentage | % |
| `network_in_rate` | Network input rate | bytes/s |
| `network_out_rate` | Network output rate | bytes/s |

### SSE Metrics

| Metric | Description | Unit |
|--------|-------------|------|
| `events_sent` | Total SSE events sent | count |
| `events_received` | Total SSE events received | count |
| `stream_errors` | Total stream errors | count |
| `keepalive_sent` | Total keepalive messages sent | count |
| `client_disconnects` | Total client disconnections | count |

### Tool Metrics

| Metric | Description | Unit |
|--------|-------------|------|
| `tool_calls_total` | Total tool calls | count |
| `tool_calls_success` | Successful tool calls | count |
| `tool_calls_error` | Failed tool calls | count |
| `tool_calls_timeout` | Timed out tool calls | count |
| `tool_execution_time_avg` | Average execution time | seconds |

## Alerting

### Alert Severity Levels

- **Info**: Informational alerts, no action required
- **Warning**: Performance degradation, monitor closely
- **Critical**: Serious performance issues, immediate attention needed
- **Emergency**: System failure or critical performance degradation

### Default Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| CPU Usage | 70% | 85% |
| Memory Usage | 80% | 90% |
| Response Time (P95) | 1000ms | 2000ms |
| Error Rate | 5% | 10% |
| Connection Errors | 10 | 50 |
| Tool Timeout Rate | 2% | 5% |

### Custom Alert Handlers

You can add custom alert handlers:

```python
from metrics.alerts import log_alert_handler, webhook_alert_handler

# Add log handler
server.alert_manager.add_alert_handler(log_alert_handler)

# Add webhook handler
async def custom_webhook_handler(alert):
    await webhook_alert_handler(alert, "https://your-webhook-url.com/alerts")

server.alert_manager.add_alert_handler(custom_webhook_handler)
```

## Performance Impact

The metrics system is designed for minimal performance impact:

- **Collection Overhead**: < 1% CPU usage during normal operation
- **Memory Usage**: ~50MB for in-memory storage with 24-hour retention
- **Storage**: ~10MB per day for file-based storage with compression
- **Network**: Minimal bandwidth usage for dashboard updates

## Best Practices

### Production Deployment

1. **Use File Storage**: Switch from memory to file storage for persistence
2. **Configure Retention**: Set appropriate retention periods based on your needs
3. **Monitor Alerts**: Set up alert handlers for critical thresholds
4. **Regular Cleanup**: Enable automatic cleanup of old metrics data
5. **Dashboard Access**: Secure dashboard access in production environments

### Performance Optimization

1. **Collection Interval**: Use longer intervals (30-60s) in production
2. **Storage Compression**: Enable compression for large datasets
3. **Alert Thresholds**: Tune thresholds based on your workload patterns
4. **Resource Limits**: Monitor metrics system resource usage

### Monitoring Strategy

1. **Baseline Establishment**: Run for 24-48 hours to establish baselines
2. **Threshold Tuning**: Adjust alert thresholds based on observed patterns
3. **Trend Analysis**: Use historical data to identify performance trends
4. **Capacity Planning**: Use metrics for capacity planning decisions

## Troubleshooting

For comprehensive troubleshooting procedures, see the [Troubleshooting Guide](TROUBLESHOOTING.md) and [Troubleshooting Scripts](TROUBLESHOOTING_SCRIPTS.md).

### Common Issues

#### Metrics Not Collecting
- Check if metrics are enabled in configuration
- Verify metrics system initialization in logs
- Ensure proper permissions for storage directories
- Use the [Diagnostic Script](TROUBLESHOOTING_SCRIPTS.md#diagnostic-script) to identify configuration issues

#### Dashboard Not Loading
- Verify dashboard is enabled in configuration
- Check browser console for JavaScript errors
- Ensure WebSocket connections are not blocked
- Test with the [Performance Monitoring Script](TROUBLESHOOTING_SCRIPTS.md#performance-monitoring-script)

#### High Memory Usage
- Reduce retention period
- Enable compression
- Increase collection interval
- Use the [Service Recovery Script](TROUBLESHOOTING_SCRIPTS.md#service-recovery-script) to reset metrics system

#### Missing Metrics
- Check metrics availability flags in logs
- Verify all dependencies are installed
- Review error logs for initialization issues
- Use the [Log Analysis Script](TROUBLESHOOTING_SCRIPTS.md#log-analysis-script) to identify patterns

### Debug Mode

Enable debug logging for metrics:

```yaml
logging:
  level: "DEBUG"
```

This will provide detailed information about metrics collection and processing.

## Integration Examples

### Prometheus Integration

Add to your Prometheus configuration:

```yaml
scrape_configs:
  - job_name: 'docling-mcp'
    static_configs:
      - targets: ['localhost:3020']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### Grafana Dashboard

Import the provided Grafana dashboard JSON (available in `metrics/grafana/` directory) for visualizing Docling MCP metrics.

### Custom Monitoring

Access metrics programmatically:

```python
from metrics.collector import MetricsCollector

# Get current metrics snapshot
snapshot = collector.get_current_metrics()

# Get metrics history
history = collector.get_metrics_history(hours=24)

# Export to file
storage.export_to_json("/path/to/export.json")
```

## Support

For issues or questions regarding the performance monitoring system:

1. Check the troubleshooting section above
2. Review the logs for error messages
3. Verify configuration settings
4. Ensure all dependencies are properly installed

The metrics system is designed to be self-monitoring and will log any issues it encounters during operation.