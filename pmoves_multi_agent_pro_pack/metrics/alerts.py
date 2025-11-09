"""
Alert Manager - Handles performance alerting with configurable thresholds.
"""

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
import logging
import threading

from .types import PerformanceAlert, AlertSeverity, MetricsSnapshot, MetricsConfig

logger = logging.getLogger(__name__)


class AlertManager:
    """Manages performance alerts with configurable thresholds."""
    
    def __init__(self, config: MetricsConfig, collector):
        """Initialize alert manager."""
        self.config = config
        self.collector = collector
        self.enabled = config.alerting_enabled
        self.thresholds = config.alert_thresholds
        
        # Active alerts
        self._active_alerts: Dict[str, PerformanceAlert] = {}
        self._alert_history: List[PerformanceAlert] = []
        self._max_history_size = 1000
        
        # Alert handlers
        self._alert_handlers: List[Callable[[PerformanceAlert], None]] = []
        
        # Background monitoring
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        self._check_interval = 30  # seconds
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info("AlertManager initialized")
    
    def start(self) -> None:
        """Start alert monitoring."""
        if not self.enabled:
            logger.info("Alerting is disabled")
            return
        
        self._running = True
        if asyncio.get_event_loop().is_running():
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Alert monitoring started")
    
    def stop(self) -> None:
        """Stop alert monitoring."""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
        logger.info("Alert monitoring stopped")
    
    async def _monitoring_loop(self) -> None:
        """Background loop for alert monitoring."""
        try:
            while self._running:
                await self._check_alerts()
                await asyncio.sleep(self._check_interval)
        except asyncio.CancelledError:
            logger.info("Alert monitoring loop cancelled")
        except Exception as e:
            logger.error(f"Error in alert monitoring loop: {e}")
    
    async def _check_alerts(self) -> None:
        """Check all configured alert thresholds."""
        try:
            snapshot = self.collector.get_current_metrics()
            if not snapshot:
                return
            
            # Check each metric against thresholds
            await self._check_cpu_usage(snapshot)
            await self._check_memory_usage(snapshot)
            await self._check_response_time(snapshot)
            await self._check_error_rate(snapshot)
            await self._check_connection_errors(snapshot)
            await self._check_tool_timeout_rate(snapshot)
            
            # Auto-resolve alerts that are no longer valid
            self._auto_resolve_alerts(snapshot)
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    async def _check_cpu_usage(self, snapshot: MetricsSnapshot) -> None:
        """Check CPU usage against thresholds."""
        metric_name = "cpu_usage_percent"
        current_value = snapshot.resource_metrics.cpu_usage_percent
        
        thresholds = self.thresholds.get(metric_name, {})
        warning_threshold = thresholds.get("warning", 70.0)
        critical_threshold = thresholds.get("critical", 85.0)
        
        if current_value >= critical_threshold:
            await self._create_alert(
                severity=AlertSeverity.CRITICAL,
                metric_name=metric_name,
                current_value=current_value,
                threshold_value=critical_threshold,
                message=f"CPU usage is critically high: {current_value:.1f}%"
            )
        elif current_value >= warning_threshold:
            await self._create_alert(
                severity=AlertSeverity.WARNING,
                metric_name=metric_name,
                current_value=current_value,
                threshold_value=warning_threshold,
                message=f"CPU usage is high: {current_value:.1f}%"
            )
    
    async def _check_memory_usage(self, snapshot: MetricsSnapshot) -> None:
        """Check memory usage against thresholds."""
        metric_name = "memory_usage_percent"
        current_value = snapshot.resource_metrics.memory_usage_percent
        
        thresholds = self.thresholds.get(metric_name, {})
        warning_threshold = thresholds.get("warning", 80.0)
        critical_threshold = thresholds.get("critical", 90.0)
        
        if current_value >= critical_threshold:
            await self._create_alert(
                severity=AlertSeverity.CRITICAL,
                metric_name=metric_name,
                current_value=current_value,
                threshold_value=critical_threshold,
                message=f"Memory usage is critically high: {current_value:.1f}%"
            )
        elif current_value >= warning_threshold:
            await self._create_alert(
                severity=AlertSeverity.WARNING,
                metric_name=metric_name,
                current_value=current_value,
                threshold_value=warning_threshold,
                message=f"Memory usage is high: {current_value:.1f}%"
            )
    
    async def _check_response_time(self, snapshot: MetricsSnapshot) -> None:
        """Check response time against thresholds."""
        metric_name = "response_time_p95"
        current_value = snapshot.request_metrics.response_time_p95 * 1000  # Convert to milliseconds
        
        thresholds = self.thresholds.get(metric_name, {})
        warning_threshold = thresholds.get("warning", 1000.0)
        critical_threshold = thresholds.get("critical", 2000.0)
        
        if current_value >= critical_threshold:
            await self._create_alert(
                severity=AlertSeverity.CRITICAL,
                metric_name=metric_name,
                current_value=current_value,
                threshold_value=critical_threshold,
                message=f"Response time (P95) is critically high: {current_value:.0f}ms"
            )
        elif current_value >= warning_threshold:
            await self._create_alert(
                severity=AlertSeverity.WARNING,
                metric_name=metric_name,
                current_value=current_value,
                threshold_value=warning_threshold,
                message=f"Response time (P95) is high: {current_value:.0f}ms"
            )
    
    async def _check_error_rate(self, snapshot: MetricsSnapshot) -> None:
        """Check error rate against thresholds."""
        metric_name = "error_rate"
        current_value = snapshot.request_metrics.error_rate
        
        thresholds = self.thresholds.get(metric_name, {})
        warning_threshold = thresholds.get("warning", 5.0)
        critical_threshold = thresholds.get("critical", 10.0)
        
        if current_value >= critical_threshold:
            await self._create_alert(
                severity=AlertSeverity.CRITICAL,
                metric_name=metric_name,
                current_value=current_value,
                threshold_value=critical_threshold,
                message=f"Error rate is critically high: {current_value:.1f}%"
            )
        elif current_value >= warning_threshold:
            await self._create_alert(
                severity=AlertSeverity.WARNING,
                metric_name=metric_name,
                current_value=current_value,
                threshold_value=warning_threshold,
                message=f"Error rate is high: {current_value:.1f}%"
            )
    
    async def _check_connection_errors(self, snapshot: MetricsSnapshot) -> None:
        """Check connection errors against thresholds."""
        metric_name = "connection_errors"
        current_value = snapshot.connection_metrics.connection_errors
        
        thresholds = self.thresholds.get(metric_name, {})
        warning_threshold = thresholds.get("warning", 10)
        critical_threshold = thresholds.get("critical", 50)
        
        if current_value >= critical_threshold:
            await self._create_alert(
                severity=AlertSeverity.CRITICAL,
                metric_name=metric_name,
                current_value=current_value,
                threshold_value=critical_threshold,
                message=f"Connection errors are critically high: {current_value}"
            )
        elif current_value >= warning_threshold:
            await self._create_alert(
                severity=AlertSeverity.WARNING,
                metric_name=metric_name,
                current_value=current_value,
                threshold_value=warning_threshold,
                message=f"Connection errors are high: {current_value}"
            )
    
    async def _check_tool_timeout_rate(self, snapshot: MetricsSnapshot) -> None:
        """Check tool timeout rate against thresholds."""
        metric_name = "tool_timeout_rate"
        total_calls = snapshot.tool_metrics.tool_calls_total
        timeouts = snapshot.tool_metrics.tool_calls_timeout
        
        if total_calls > 0:
            current_value = (timeouts / total_calls) * 100.0
        else:
            current_value = 0.0
        
        thresholds = self.thresholds.get(metric_name, {})
        warning_threshold = thresholds.get("warning", 2.0)
        critical_threshold = thresholds.get("critical", 5.0)
        
        if current_value >= critical_threshold:
            await self._create_alert(
                severity=AlertSeverity.CRITICAL,
                metric_name=metric_name,
                current_value=current_value,
                threshold_value=critical_threshold,
                message=f"Tool timeout rate is critically high: {current_value:.1f}%"
            )
        elif current_value >= warning_threshold:
            await self._create_alert(
                severity=AlertSeverity.WARNING,
                metric_name=metric_name,
                current_value=current_value,
                threshold_value=warning_threshold,
                message=f"Tool timeout rate is high: {current_value:.1f}%"
            )
    
    async def _create_alert(self, severity: AlertSeverity, metric_name: str,
                           current_value: float, threshold_value: float,
                           message: str, labels: Optional[Dict[str, str]] = None) -> None:
        """Create a new performance alert."""
        try:
            alert_id = str(uuid.uuid4())
            
            alert = PerformanceAlert(
                alert_id=alert_id,
                severity=severity,
                metric_name=metric_name,
                current_value=current_value,
                threshold_value=threshold_value,
                message=message,
                timestamp=datetime.now(),
                labels=labels or {},
                acknowledged=False,
                resolved=False
            )
            
            # Check if similar alert already exists
            existing_alert = self._find_similar_alert(metric_name, severity)
            
            if existing_alert:
                # Update existing alert
                with self._lock:
                    existing_alert.current_value = current_value
                    existing_alert.timestamp = datetime.now()
                    existing_alert.message = message
                logger.info(f"Updated existing alert: {existing_alert.alert_id}")
            else:
                # Create new alert
                with self._lock:
                    self._active_alerts[alert_id] = alert
                    self._alert_history.append(alert)
                    
                    # Trim history
                    if len(self._alert_history) > self._max_history_size:
                        self._alert_history = self._alert_history[-self._max_history_size:]
                
                logger.warning(f"Created new alert: {alert_id} - {message}")
                
                # Notify handlers
                await self._notify_handlers(alert)
            
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
    
    def _find_similar_alert(self, metric_name: str, severity: AlertSeverity) -> Optional[PerformanceAlert]:
        """Find an existing similar alert."""
        with self._lock:
            for alert in self._active_alerts.values():
                if (alert.metric_name == metric_name and 
                    alert.severity == severity and 
                    not alert.resolved):
                    return alert
        return None
    
    def _auto_resolve_alerts(self, snapshot: MetricsSnapshot) -> None:
        """Automatically resolve alerts that are no longer valid."""
        try:
            with self._lock:
                alerts_to_resolve = []
                
                for alert in self._active_alerts.values():
                    if alert.resolved:
                        continue
                    
                    # Check if alert condition is no longer met
                    if self._is_alert_resolved(alert, snapshot):
                        alerts_to_resolve.append(alert)
                
                # Resolve alerts
                for alert in alerts_to_resolve:
                    alert.resolved = True
                    alert.resolved_at = datetime.now()
                    logger.info(f"Auto-resolved alert: {alert.alert_id}")
                    
        except Exception as e:
            logger.error(f"Error auto-resolving alerts: {e}")
    
    def _is_alert_resolved(self, alert: PerformanceAlert, snapshot: MetricsSnapshot) -> bool:
        """Check if an alert condition is resolved."""
        try:
            metric_name = alert.metric_name
            current_value = self._get_metric_value(metric_name, snapshot)
            
            if current_value is None:
                return False
            
            # Alert is resolved if current value is below warning threshold
            thresholds = self.thresholds.get(metric_name, {})
            warning_threshold = thresholds.get("warning", 0)
            
            if alert.severity == AlertSeverity.CRITICAL:
                # Critical alert resolves when value drops below warning threshold
                return current_value < warning_threshold
            elif alert.severity == AlertSeverity.WARNING:
                # Warning alert resolves when value drops below 80% of warning threshold
                return current_value < (warning_threshold * 0.8)
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking if alert is resolved: {e}")
            return False
    
    def _get_metric_value(self, metric_name: str, snapshot: MetricsSnapshot) -> Optional[float]:
        """Get current value for a metric."""
        try:
            if metric_name == "cpu_usage_percent":
                return snapshot.resource_metrics.cpu_usage_percent
            elif metric_name == "memory_usage_percent":
                return snapshot.resource_metrics.memory_usage_percent
            elif metric_name == "response_time_p95":
                return snapshot.request_metrics.response_time_p95 * 1000  # Convert to ms
            elif metric_name == "error_rate":
                return snapshot.request_metrics.error_rate
            elif metric_name == "connection_errors":
                return float(snapshot.connection_metrics.connection_errors)
            elif metric_name == "tool_timeout_rate":
                total_calls = snapshot.tool_metrics.tool_calls_total
                timeouts = snapshot.tool_metrics.tool_calls_timeout
                return (timeouts / total_calls * 100.0) if total_calls > 0 else 0.0
            else:
                return None
        except Exception:
            return None
    
    async def _notify_handlers(self, alert: PerformanceAlert) -> None:
        """Notify all registered alert handlers."""
        try:
            for handler in self._alert_handlers:
                try:
                    # Support both sync and async handlers
                    if asyncio.iscoroutinefunction(handler):
                        await handler(alert)
                    else:
                        handler(alert)
                except Exception as e:
                    logger.error(f"Error in alert handler: {e}")
                    
        except Exception as e:
            logger.error(f"Error notifying handlers: {e}")
    
    def add_alert_handler(self, handler: Callable[[PerformanceAlert], None]) -> None:
        """Add an alert handler."""
        self._alert_handlers.append(handler)
        logger.info("Added alert handler")
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        try:
            with self._lock:
                if alert_id in self._active_alerts:
                    self._active_alerts[alert_id].acknowledged = True
                    logger.info(f"Acknowledged alert: {alert_id}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error acknowledging alert: {e}")
            return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Manually resolve an alert."""
        try:
            with self._lock:
                if alert_id in self._active_alerts:
                    alert = self._active_alerts[alert_id]
                    alert.resolved = True
                    alert.resolved_at = datetime.now()
                    logger.info(f"Resolved alert: {alert_id}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
            return False
    
    def get_active_alerts(self) -> List[PerformanceAlert]:
        """Get all active alerts."""
        with self._lock:
            return [alert for alert in self._active_alerts.values() if not alert.resolved]
    
    def get_alert_history(self, limit: Optional[int] = None) -> List[PerformanceAlert]:
        """Get alert history."""
        with self._lock:
            alerts = list(self._alert_history)
            if limit:
                alerts = alerts[-limit:]
            return alerts
    
    def get_alerts_by_severity(self, severity: AlertSeverity) -> List[PerformanceAlert]:
        """Get alerts by severity."""
        with self._lock:
            return [alert for alert in self._active_alerts.values() 
                   if alert.severity == severity and not alert.resolved]
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of current alert status."""
        try:
            with self._lock:
                active_alerts = self.get_active_alerts()
                
                summary = {
                    'total_active': len(active_alerts),
                    'by_severity': {
                        'emergency': len([a for a in active_alerts if a.severity == AlertSeverity.EMERGENCY]),
                        'critical': len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]),
                        'warning': len([a for a in active_alerts if a.severity == AlertSeverity.WARNING]),
                        'info': len([a for a in active_alerts if a.severity == AlertSeverity.INFO])
                    },
                    'acknowledged': len([a for a in active_alerts if a.acknowledged]),
                    'unacknowledged': len([a for a in active_alerts if not a.acknowledged]),
                    'alerts': [self._alert_to_dict(alert) for alert in active_alerts]
                }
                
                return summary
                
        except Exception as e:
            logger.error(f"Error getting alert summary: {e}")
            return {}
    
    def _alert_to_dict(self, alert: PerformanceAlert) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            'alert_id': alert.alert_id,
            'severity': alert.severity.value,
            'metric_name': alert.metric_name,
            'current_value': alert.current_value,
            'threshold_value': alert.threshold_value,
            'message': alert.message,
            'timestamp': alert.timestamp.isoformat(),
            'labels': alert.labels,
            'acknowledged': alert.acknowledged,
            'resolved': alert.resolved,
            'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None
        }
    
    def update_thresholds(self, new_thresholds: Dict[str, Dict[str, float]]) -> None:
        """Update alert thresholds."""
        try:
            self.thresholds.update(new_thresholds)
            logger.info("Updated alert thresholds")
        except Exception as e:
            logger.error(f"Error updating thresholds: {e}")
    
    def reset_alerts(self) -> None:
        """Reset all alerts."""
        try:
            with self._lock:
                self._active_alerts.clear()
                self._alert_history.clear()
            logger.info("All alerts have been reset")
        except Exception as e:
            logger.error(f"Error resetting alerts: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status based on alerts."""
        try:
            active_alerts = self.get_active_alerts()
            
            if not active_alerts:
                status = "healthy"
                status_code = 0
            else:
                # Determine status based on highest severity alert
                severities = [alert.severity for alert in active_alerts]
                
                if AlertSeverity.EMERGENCY in severities:
                    status = "emergency"
                    status_code = 4
                elif AlertSeverity.CRITICAL in severities:
                    status = "critical"
                    status_code = 3
                elif AlertSeverity.WARNING in severities:
                    status = "warning"
                    status_code = 2
                else:
                    status = "info"
                    status_code = 1
            
            return {
                'status': status,
                'status_code': status_code,
                'active_alerts': len(active_alerts),
                'summary': self.get_alert_summary()
            }
            
        except Exception as e:
            logger.error(f"Error getting health status: {e}")
            return {'status': 'unknown', 'status_code': 5, 'error': str(e)}


# Example alert handlers
async def log_alert_handler(alert: PerformanceAlert) -> None:
    """Example alert handler that logs alerts."""
    logger.warning(f"ALERT [{alert.severity.value.upper()}] {alert.message}")


async def webhook_alert_handler(alert: PerformanceAlert, webhook_url: str) -> None:
    """Example alert handler that sends to webhook."""
    try:
        import aiohttp
        import json
        
        payload = {
            'alert_id': alert.alert_id,
            'severity': alert.severity.value,
            'message': alert.message,
            'metric_name': alert.metric_name,
            'current_value': alert.current_value,
            'threshold_value': alert.threshold_value,
            'timestamp': alert.timestamp.isoformat()
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as response:
                if response.status >= 400:
                    logger.error(f"Webhook alert failed: {response.status}")
                    
    except Exception as e:
        logger.error(f"Error sending webhook alert: {e}")