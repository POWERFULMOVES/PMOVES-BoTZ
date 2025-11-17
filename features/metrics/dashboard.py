"""
Metrics Dashboard - Real-time HTML dashboard for performance monitoring.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from aiohttp import web, web_response
import jinja2
import os

from .types import MetricsConfig, MetricsSnapshot
from .collector import MetricsCollector

logger = logging.getLogger(__name__)


class MetricsDashboard:
    """Real-time HTML dashboard for metrics visualization."""
    
    def __init__(self, config: MetricsConfig, collector: MetricsCollector):
        """Initialize metrics dashboard."""
        self.config = config
        self.collector = collector
        self.enabled = config.dashboard_enabled
        
        # Template engine
        self.template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(
                os.path.join(os.path.dirname(__file__), 'templates')
            ),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
        
        # WebSocket connections
        self._websocket_connections: set = set()
        
        logger.info("MetricsDashboard initialized")
    
    def get_dashboard_html(self) -> str:
        """Generate the main dashboard HTML."""
        try:
            template = self.template_env.get_template('dashboard.html')
            
            # Get current metrics
            snapshot = self.collector.get_current_metrics()
            if not snapshot:
                snapshot_data = self._get_empty_snapshot_data()
            else:
                snapshot_data = self._snapshot_to_dashboard_data(snapshot)
            
            # Render template
            html = template.render(
                title="Docling MCP Server - Performance Dashboard",
                snapshot_data=snapshot_data,
                refresh_interval=5000,  # 5 seconds
                websocket_enabled=True
            )
            
            return html
            
        except Exception as e:
            logger.error(f"Error generating dashboard HTML: {e}")
            return self._get_error_html(str(e))
    
    def _get_empty_snapshot_data(self) -> Dict[str, Any]:
        """Get empty snapshot data for when no metrics are available."""
        return {
            'timestamp': datetime.now().isoformat(),
            'connection_metrics': {
                'active_connections': 0,
                'total_connections': 0,
                'connection_duration_avg': 0,
                'connection_success_rate': 100
            },
            'request_metrics': {
                'request_count': 0,
                'request_rate': 0,
                'response_time_avg': 0,
                'response_time_p95': 0,
                'success_rate': 100,
                'error_rate': 0
            },
            'resource_metrics': {
                'cpu_usage_percent': 0,
                'memory_usage_percent': 0,
                'memory_usage_bytes': 0,
                'disk_usage_percent': 0
            },
            'sse_metrics': {
                'events_sent': 0,
                'events_received': 0,
                'stream_errors': 0,
                'keepalive_sent': 0
            },
            'tool_metrics': {
                'tool_calls_total': 0,
                'tool_calls_success': 0,
                'tool_calls_error': 0,
                'tool_execution_time_avg': 0
            },
            'system_metrics': {
                'uptime_seconds': 0,
                'health_check_failures': 0,
                'error_count_total': 0
            }
        }
    
    def _snapshot_to_dashboard_data(self, snapshot: MetricsSnapshot) -> Dict[str, Any]:
        """Convert snapshot to dashboard data format."""
        return {
            'timestamp': snapshot.timestamp.isoformat(),
            'connection_metrics': {
                'active_connections': snapshot.connection_metrics.active_connections,
                'total_connections': snapshot.connection_metrics.total_connections,
                'connection_duration_avg': round(snapshot.connection_metrics.connection_duration_avg, 2),
                'connection_success_rate': round(snapshot.connection_metrics.connection_success_rate, 1)
            },
            'request_metrics': {
                'request_count': snapshot.request_metrics.request_count,
                'request_rate': round(snapshot.request_metrics.request_rate, 2),
                'response_time_avg': round(snapshot.request_metrics.response_time_avg * 1000, 0),  # ms
                'response_time_p95': round(snapshot.request_metrics.response_time_p95 * 1000, 0),  # ms
                'success_rate': round(snapshot.request_metrics.success_rate, 1),
                'error_rate': round(snapshot.request_metrics.error_rate, 1)
            },
            'resource_metrics': {
                'cpu_usage_percent': round(snapshot.resource_metrics.cpu_usage_percent, 1),
                'memory_usage_percent': round(snapshot.resource_metrics.memory_usage_percent, 1),
                'memory_usage_bytes': snapshot.resource_metrics.memory_usage_bytes,
                'memory_usage_mb': round(snapshot.resource_metrics.memory_usage_bytes / (1024 * 1024), 1),
                'disk_usage_percent': round(snapshot.resource_metrics.disk_usage_percent, 1)
            },
            'sse_metrics': {
                'events_sent': snapshot.sse_metrics.events_sent,
                'events_received': snapshot.sse_metrics.events_received,
                'stream_errors': snapshot.sse_metrics.stream_errors,
                'keepalive_sent': snapshot.sse_metrics.keepalive_sent,
                'client_disconnects': snapshot.sse_metrics.client_disconnects
            },
            'tool_metrics': {
                'tool_calls_total': snapshot.tool_metrics.tool_calls_total,
                'tool_calls_success': snapshot.tool_metrics.tool_calls_success,
                'tool_calls_error': snapshot.tool_metrics.tool_calls_error,
                'tool_calls_timeout': snapshot.tool_metrics.tool_calls_timeout,
                'tool_execution_time_avg': round(snapshot.tool_metrics.tool_execution_time_avg * 1000, 0)  # ms
            },
            'system_metrics': {
                'uptime_seconds': round(snapshot.system_metrics.uptime_seconds, 0),
                'uptime_hours': round(snapshot.system_metrics.uptime_seconds / 3600, 1),
                'health_check_failures': snapshot.system_metrics.health_check_failures,
                'error_count_total': snapshot.system_metrics.error_count_total,
                'warning_count_total': snapshot.system_metrics.warning_count_total
            }
        }
    
    def _get_error_html(self, error_message: str) -> str:
        """Get error HTML page."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Dashboard Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 50px; }}
                .error {{ color: red; padding: 20px; border: 1px solid red; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <h1>Dashboard Error</h1>
            <div class="error">
                <p>Unable to load metrics dashboard:</p>
                <p>{error_message}</p>
            </div>
        </body>
        </html>
        """
    
    async def handle_dashboard_request(self, request: web.Request) -> web.Response:
        """Handle dashboard HTTP request."""
        try:
            html = self.get_dashboard_html()
            return web.Response(text=html, content_type="text/html")
            
        except Exception as e:
            logger.error(f"Error handling dashboard request: {e}")
            error_html = self._get_error_html(str(e))
            return web.Response(text=error_html, content_type="text/html", status=500)
    
    async def handle_metrics_data_request(self, request: web.Request) -> web.Response:
        """Handle metrics data JSON request."""
        try:
            snapshot = self.collector.get_current_metrics()
            if not snapshot:
                data = self._get_empty_snapshot_data()
            else:
                data = self._snapshot_to_dashboard_data(snapshot)
            
            return web.Response(
                text=json.dumps(data),
                content_type="application/json"
            )
            
        except Exception as e:
            logger.error(f"Error handling metrics data request: {e}")
            return web.Response(
                text=json.dumps({"error": str(e)}),
                content_type="application/json",
                status=500
            )
    
    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connections for real-time updates."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self._websocket_connections.add(ws)
        logger.info(f"WebSocket client connected. Total connections: {len(self._websocket_connections)}")
        
        try:
            # Send initial data
            snapshot = self.collector.get_current_metrics()
            if snapshot:
                data = self._snapshot_to_dashboard_data(snapshot)
                await ws.send_str(json.dumps({
                    'type': 'metrics_update',
                    'data': data
                }))
            
            # Keep connection alive and handle messages
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    # Handle ping/pong or other messages if needed
                    if msg.data == 'ping':
                        await ws.send_str('pong')
                elif msg.type == web.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
                    
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            self._websocket_connections.discard(ws)
            logger.info(f"WebSocket client disconnected. Total connections: {len(self._websocket_connections)}")
        
        return ws
    
    async def broadcast_metrics_update(self) -> None:
        """Broadcast metrics update to all connected WebSocket clients."""
        if not self._websocket_connections:
            return
        
        try:
            snapshot = self.collector.get_current_metrics()
            if not snapshot:
                return
            
            data = self._snapshot_to_dashboard_data(snapshot)
            message = json.dumps({
                'type': 'metrics_update',
                'data': data
            })
            
            # Send to all connected clients
            disconnected = set()
            for ws in self._websocket_connections:
                try:
                    await ws.send_str(message)
                except ConnectionResetError:
                    disconnected.add(ws)
                except Exception as e:
                    logger.error(f"Error sending to WebSocket client: {e}")
                    disconnected.add(ws)
            
            # Remove disconnected clients
            self._websocket_connections -= disconnected
            
        except Exception as e:
            logger.error(f"Error broadcasting metrics update: {e}")
    
    def setup_routes(self, app: web.Application) -> None:
        """Setup HTTP routes for dashboard."""
        if not self.enabled:
            return
        
        # Dashboard main page
        app.router.add_get(self.config.dashboard_endpoint, self.handle_dashboard_request)
        
        # Metrics data endpoint
        app.router.add_get(f"{self.config.dashboard_endpoint}/data", self.handle_metrics_data_request)
        
        # WebSocket endpoint
        app.router.add_get(f"{self.config.dashboard_endpoint}/ws", self.handle_websocket)
        
        logger.info(f"Dashboard endpoints configured:")
        logger.info(f"  Main: {self.config.dashboard_endpoint}")
        logger.info(f"  Data: {self.config.dashboard_endpoint}/data")
        logger.info(f"  WebSocket: {self.config.dashboard_endpoint}/ws")


# Create dashboard template directory and files
def create_dashboard_templates():
    """Create dashboard HTML templates."""
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(templates_dir, exist_ok=True)
    
    # Main dashboard template
    dashboard_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            font-size: 1.5rem;
            font-weight: 600;
        }
        
        .header .subtitle {
            opacity: 0.9;
            font-size: 0.9rem;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .metric-card {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s ease;
        }
        
        .metric-card:hover {
            transform: translateY(-2px);
        }
        
        .metric-card h3 {
            color: #555;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 1rem;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 0.5rem;
        }
        
        .metric-value {
            font-size: 2rem;
            font-weight: 700;
            color: #333;
            margin-bottom: 0.5rem;
        }
        
        .metric-unit {
            font-size: 0.8rem;
            color: #666;
            margin-left: 0.25rem;
        }
        
        .metric-trend {
            font-size: 0.8rem;
            margin-top: 0.5rem;
        }
        
        .trend-up {
            color: #e74c3c;
        }
        
        .trend-down {
            color: #27ae60;
        }
        
        .trend-stable {
            color: #3498db;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 0.5rem;
        }
        
        .status-healthy {
            background-color: #27ae60;
        }
        
        .status-warning {
            background-color: #f39c12;
        }
        
        .status-critical {
            background-color: #e74c3c;
        }
        
        .status-unknown {
            background-color: #95a5a6;
        }
        
        .connection-status {
            display: flex;
            align-items: center;
            margin-bottom: 1rem;
            padding: 0.5rem;
            background-color: #f8f9fa;
            border-radius: 4px;
        }
        
        .timestamp {
            text-align: right;
            color: #666;
            font-size: 0.8rem;
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid #eee;
        }
        
        .chart-container {
            height: 200px;
            margin-top: 1rem;
            background-color: #f8f9fa;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #666;
        }
        
        .loading {
            text-align: center;
            padding: 2rem;
            color: #666;
        }
        
        .error {
            background-color: #fee;
            border: 1px solid #fcc;
            color: #c33;
            padding: 1rem;
            border-radius: 4px;
            margin: 1rem 0;
        }
        
        .refresh-indicator {
            position: fixed;
            top: 1rem;
            right: 1rem;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            font-size: 0.8rem;
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        
        .refresh-indicator.show {
            opacity: 1;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }
            
            .metrics-grid {
                grid-template-columns: 1fr;
            }
            
            .header {
                padding: 1rem;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Docling MCP Server</h1>
        <div class="subtitle">Performance Monitoring Dashboard</div>
    </div>
    
    <div class="container">
        <div class="connection-status">
            <span id="connection-indicator" class="status-indicator status-unknown"></span>
            <span id="connection-text">Connecting...</span>
        </div>
        
        <div id="metrics-container" class="loading">
            Loading metrics...
        </div>
        
        <div class="timestamp">
            Last updated: <span id="last-update">-</span>
        </div>
    </div>
    
    <div id="refresh-indicator" class="refresh-indicator">
        Updating...
    </div>
    
    <script>
        class MetricsDashboard {
            constructor() {
                this.ws = null;
                this.reconnectInterval = 5000;
                this.updateInterval = 5000;
                this.metricsData = null;
                this.updateTimer = null;
                this.reconnectTimer = null;
                
                this.init();
            }
            
            init() {
                this.connectWebSocket();
                this.startPeriodicUpdates();
            }
            
            connectWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}{{ dashboard_endpoint }}/ws`;
                
                try {
                    this.ws = new WebSocket(wsUrl);
                    
                    this.ws.onopen = () => {
                        console.log('WebSocket connected');
                        this.updateConnectionStatus('connected');
                        this.loadMetrics();
                    };
                    
                    this.ws.onmessage = (event) => {
                        try {
                            const message = JSON.parse(event.data);
                            if (message.type === 'metrics_update') {
                                this.updateMetrics(message.data);
                            }
                        } catch (error) {
                            console.error('Error parsing WebSocket message:', error);
                        }
                    };
                    
                    this.ws.onclose = () => {
                        console.log('WebSocket disconnected');
                        this.updateConnectionStatus('disconnected');
                        this.scheduleReconnect();
                    };
                    
                    this.ws.onerror = (error) => {
                        console.error('WebSocket error:', error);
                        this.updateConnectionStatus('error');
                    };
                    
                } catch (error) {
                    console.error('Error creating WebSocket:', error);
                    this.updateConnectionStatus('error');
                    this.scheduleReconnect();
                }
            }
            
            scheduleReconnect() {
                if (this.reconnectTimer) {
                    clearTimeout(this.reconnectTimer);
                }
                
                this.reconnectTimer = setTimeout(() => {
                    console.log('Attempting to reconnect WebSocket...');
                    this.connectWebSocket();
                }, this.reconnectInterval);
            }
            
            startPeriodicUpdates() {
                this.updateTimer = setInterval(() => {
                    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
                        this.loadMetrics();
                    }
                }, this.updateInterval);
            }
            
            async loadMetrics() {
                try {
                    const response = await fetch('{{ dashboard_endpoint }}/data');
                    const data = await response.json();
                    
                    if (data.error) {
                        throw new Error(data.error);
                    }
                    
                    this.updateMetrics(data);
                } catch (error) {
                    console.error('Error loading metrics:', error);
                    this.showError('Failed to load metrics: ' + error.message);
                }
            }
            
            updateMetrics(data) {
                this.metricsData = data;
                this.renderMetrics();
                this.updateTimestamp();
                this.showRefreshIndicator();
            }
            
            renderMetrics() {
                if (!this.metricsData) return;
                
                const container = document.getElementById('metrics-container');
                const data = this.metricsData;
                
                container.innerHTML = `
                    <div class="metrics-grid">
                        ${this.renderConnectionMetrics(data.connection_metrics)}
                        ${this.renderRequestMetrics(data.request_metrics)}
                        ${this.renderResourceMetrics(data.resource_metrics)}
                        ${this.renderSSEMetrics(data.sse_metrics)}
                        ${this.renderToolMetrics(data.tool_metrics)}
                        ${this.renderSystemMetrics(data.system_metrics)}
                    </div>
                `;
            }
            
            renderConnectionMetrics(metrics) {
                return `
                    <div class="metric-card">
                        <h3>Connections</h3>
                        <div class="metric-value">
                            ${metrics.active_connections}
                            <span class="metric-unit">active</span>
                        </div>
                        <div>Total: ${metrics.total_connections}</div>
                        <div>Success Rate: ${metrics.connection_success_rate}%</div>
                        <div>Avg Duration: ${metrics.connection_duration_avg}s</div>
                    </div>
                `;
            }
            
            renderRequestMetrics(metrics) {
                return `
                    <div class="metric-card">
                        <h3>Requests</h3>
                        <div class="metric-value">
                            ${metrics.request_rate}
                            <span class="metric-unit">req/s</span>
                        </div>
                        <div>Total: ${metrics.request_count}</div>
                        <div>Success Rate: ${metrics.success_rate}%</div>
                        <div>P95 Response: ${metrics.response_time_p95}ms</div>
                        <div>Error Rate: ${metrics.error_rate}%</div>
                    </div>
                `;
            }
            
            renderResourceMetrics(metrics) {
                const cpuStatus = metrics.cpu_usage_percent > 80 ? 'critical' : 
                                 metrics.cpu_usage_percent > 60 ? 'warning' : 'healthy';
                const memoryStatus = metrics.memory_usage_percent > 80 ? 'critical' : 
                                    metrics.memory_usage_percent > 60 ? 'warning' : 'healthy';
                
                return `
                    <div class="metric-card">
                        <h3>Resources</h3>
                        <div class="metric-value">
                            ${metrics.cpu_usage_percent}%
                            <span class="metric-unit">CPU</span>
                        </div>
                        <div class="metric-value">
                            ${metrics.memory_usage_percent}%
                            <span class="metric-unit">Memory</span>
                        </div>
                        <div>${metrics.memory_usage_mb} MB used</div>
                        <div>Disk: ${metrics.disk_usage_percent}%</div>
                    </div>
                `;
            }
            
            renderSSEMetrics(metrics) {
                return `
                    <div class="metric-card">
                        <h3>SSE Events</h3>
                        <div class="metric-value">
                            ${metrics.events_sent}
                            <span class="metric-unit">sent</span>
                        </div>
                        <div>Received: ${metrics.events_received}</div>
                        <div>Errors: ${metrics.stream_errors}</div>
                        <div>Keepalives: ${metrics.keepalive_sent}</div>
                        <div>Disconnects: ${metrics.client_disconnects}</div>
                    </div>
                `;
            }
            
            renderToolMetrics(metrics) {
                return `
                    <div class="metric-card">
                        <h3>Tool Calls</h3>
                        <div class="metric-value">
                            ${metrics.tool_calls_total}
                            <span class="metric-unit">total</span>
                        </div>
                        <div>Success: ${metrics.tool_calls_success}</div>
                        <div>Errors: ${metrics.tool_calls_error}</div>
                        <div>Timeouts: ${metrics.tool_calls_timeout}</div>
                        <div>Avg Time: ${metrics.tool_execution_time_avg}ms</div>
                    </div>
                `;
            }
            
            renderSystemMetrics(metrics) {
                return `
                    <div class="metric-card">
                        <h3>System</h3>
                        <div class="metric-value">
                            ${metrics.uptime_hours}
                            <span class="metric-unit">hours</span>
                        </div>
                        <div>Health Failures: ${metrics.health_check_failures}</div>
                        <div>Total Errors: ${metrics.error_count_total}</div>
                        <div>Total Warnings: ${metrics.warning_count_total}</div>
                    </div>
                `;
            }
            
            updateConnectionStatus(status) {
                const indicator = document.getElementById('connection-indicator');
                const text = document.getElementById('connection-text');
                
                indicator.className = 'status-indicator';
                
                switch (status) {
                    case 'connected':
                        indicator.classList.add('status-healthy');
                        text.textContent = 'Connected (WebSocket)';
                        break;
                    case 'disconnected':
                        indicator.classList.add('status-unknown');
                        text.textContent = 'Disconnected';
                        break;
                    case 'error':
                        indicator.classList.add('status-critical');
                        text.textContent = 'Connection Error';
                        break;
                    default:
                        indicator.classList.add('status-unknown');
                        text.textContent = 'Unknown Status';
                }
            }
            
            updateTimestamp() {
                const timestamp = this.metricsData ? this.metricsData.timestamp : new Date().toISOString();
                document.getElementById('last-update').textContent = new Date(timestamp).toLocaleString();
            }
            
            showRefreshIndicator() {
                const indicator = document.getElementById('refresh-indicator');
                indicator.classList.add('show');
                setTimeout(() => {
                    indicator.classList.remove('show');
                }, 1000);
            }
            
            showError(message) {
                const container = document.getElementById('metrics-container');
                container.innerHTML = `<div class="error">${message}</div>`;
            }
            
            destroy() {
                if (this.ws) {
                    this.ws.close();
                }
                if (this.updateTimer) {
                    clearInterval(this.updateTimer);
                }
                if (this.reconnectTimer) {
                    clearTimeout(this.reconnectTimer);
                }
            }
        }
        
        // Initialize dashboard when page loads
        let dashboard;
        document.addEventListener('DOMContentLoaded', () => {
            dashboard = new MetricsDashboard();
        });
        
        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            if (dashboard) {
                dashboard.destroy();
            }
        });
    </script>
</body>
</html>
"""
    
    # Create templates directory and file
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(templates_dir, exist_ok=True)
    
    template_path = os.path.join(templates_dir, 'dashboard.html')
    with open(template_path, 'w') as f:
        f.write(dashboard_html)
    
    return dashboard_html


# Create the template file
create_dashboard_templates()