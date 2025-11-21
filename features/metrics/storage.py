"""
Metrics Storage - Handles persistent storage and retention of metrics data.
"""

import json
import csv
import os
import gzip
import shutil
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
import logging
import threading
import asyncio

from .types import MetricsSnapshot, MetricsConfig, MetricValue

logger = logging.getLogger(__name__)


class MetricsStorage:
    """Handles storage and retrieval of metrics data with configurable retention."""
    
    def __init__(self, config: MetricsConfig):
        """Initialize metrics storage."""
        self.config = config
        self.storage_path = Path(config.storage_path)
        self.storage_backend = config.storage_backend
        self.retention_hours = config.retention_hours
        self.compression_enabled = config.compression_enabled
        self.compression_threshold = config.compression_threshold
        
        # Ensure storage directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info(f"MetricsStorage initialized with backend: {self.storage_backend}")
    
    def store_snapshot(self, snapshot: MetricsSnapshot) -> None:
        """Store a metrics snapshot."""
        if not self.config.enabled:
            return
            
        try:
            if self.storage_backend == "memory":
                # Memory storage is handled by the collector
                pass
            elif self.storage_backend == "file":
                self._store_file_snapshot(snapshot)
            elif self.storage_backend == "database":
                # Database storage would be implemented here
                logger.warning("Database storage not yet implemented")
            else:
                logger.error(f"Unknown storage backend: {self.storage_backend}")
                
        except Exception as e:
            logger.error(f"Error storing metrics snapshot: {e}")
    
    def _store_file_snapshot(self, snapshot: MetricsSnapshot) -> None:
        """Store snapshot to file system."""
        try:
            timestamp = snapshot.timestamp
            date_str = timestamp.strftime("%Y%m%d")
            time_str = timestamp.strftime("%H%M%S")
            
            # Create daily directory
            daily_dir = self.storage_path / date_str
            daily_dir.mkdir(exist_ok=True)
            
            # Store as JSON file
            filename = f"metrics_{time_str}.json"
            filepath = daily_dir / filename
            
            # Convert snapshot to dictionary
            data = self._snapshot_to_dict(snapshot)
            
            # Write to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            # Check if compression is needed
            if self.compression_enabled:
                self._check_compression(daily_dir)
            
            # Clean up old files
            self._cleanup_old_files()
            
        except Exception as e:
            logger.error(f"Error storing file snapshot: {e}")
    
    def _snapshot_to_dict(self, snapshot: MetricsSnapshot) -> Dict[str, Any]:
        """Convert metrics snapshot to dictionary."""
        return {
            'timestamp': snapshot.timestamp.isoformat(),
            'connection_metrics': snapshot.connection_metrics.__dict__,
            'request_metrics': snapshot.request_metrics.__dict__,
            'resource_metrics': snapshot.resource_metrics.__dict__,
            'sse_metrics': snapshot.sse_metrics.__dict__,
            'tool_metrics': snapshot.tool_metrics.__dict__,
            'system_metrics': snapshot.system_metrics.__dict__,
            'custom_metrics': {k: v.__dict__ for k, v in snapshot.custom_metrics.items()}
        }
    
    def _dict_to_snapshot(self, data: Dict[str, Any]) -> MetricsSnapshot:
        """Convert dictionary to metrics snapshot."""
        from .types import (
            ConnectionMetrics, RequestMetrics, ResourceMetrics,
            SSEMetrics, ToolMetrics, SystemMetrics, MetricValue
        )
        
        return MetricsSnapshot(
            timestamp=datetime.fromisoformat(data['timestamp']),
            connection_metrics=ConnectionMetrics(**data['connection_metrics']),
            request_metrics=RequestMetrics(**data['request_metrics']),
            resource_metrics=ResourceMetrics(**data['resource_metrics']),
            sse_metrics=SSEMetrics(**data['sse_metrics']),
            tool_metrics=ToolMetrics(**data['tool_metrics']),
            system_metrics=SystemMetrics(**data['system_metrics']),
            custom_metrics={k: MetricValue(**v) for k, v in data.get('custom_metrics', {}).items()}
        )
    
    def _check_compression(self, daily_dir: Path) -> None:
        """Check if files in directory should be compressed."""
        try:
            json_files = list(daily_dir.glob("metrics_*.json"))
            
            if len(json_files) >= self.compression_threshold:
                # Compress older files (keep most recent uncompressed)
                files_to_compress = sorted(json_files)[:-10]  # Keep 10 most recent uncompressed
                
                for file_path in files_to_compress:
                    self._compress_file(file_path)
                    
        except Exception as e:
            logger.error(f"Error checking compression: {e}")
    
    def _compress_file(self, file_path: Path) -> None:
        """Compress a single metrics file."""
        try:
            compressed_path = file_path.with_suffix('.json.gz')
            
            with open(file_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove original file
            file_path.unlink()
            
            logger.debug(f"Compressed metrics file: {file_path.name}")
            
        except Exception as e:
            logger.error(f"Error compressing file {file_path}: {e}")
    
    def _cleanup_old_files(self) -> None:
        """Clean up files older than retention period."""
        try:
            cutoff_date = datetime.now() - timedelta(hours=self.retention_hours)
            
            for item in self.storage_path.iterdir():
                if item.is_dir():
                    try:
                        dir_date = datetime.strptime(item.name, "%Y%m%d")
                        if dir_date < cutoff_date.date():
                            shutil.rmtree(item)
                            logger.info(f"Removed old metrics directory: {item.name}")
                    except ValueError:
                        # Not a date directory, skip
                        continue
                        
        except Exception as e:
            logger.error(f"Error cleaning up old files: {e}")
    
    def get_snapshots(self, start_time: Optional[datetime] = None, 
                     end_time: Optional[datetime] = None,
                     limit: Optional[int] = None) -> List[MetricsSnapshot]:
        """Retrieve metrics snapshots within time range."""
        snapshots = []
        
        try:
            if self.storage_backend == "file":
                snapshots = self._get_file_snapshots(start_time, end_time, limit)
            elif self.storage_backend == "memory":
                # Memory storage would be handled by collector
                pass
            elif self.storage_backend == "database":
                logger.warning("Database retrieval not yet implemented")
                
        except Exception as e:
            logger.error(f"Error retrieving snapshots: {e}")
            
        return snapshots
    
    def _get_file_snapshots(self, start_time: Optional[datetime], 
                           end_time: Optional[datetime], 
                           limit: Optional[int]) -> List[MetricsSnapshot]:
        """Retrieve snapshots from file storage."""
        snapshots = []
        
        try:
            # Determine date range to search
            if not start_time:
                start_time = datetime.now() - timedelta(hours=self.retention_hours)
            if not end_time:
                end_time = datetime.now()
            
            # Iterate through date directories
            current_date = start_time.date()
            end_date = end_time.date()
            
            while current_date <= end_date:
                date_str = current_date.strftime("%Y%m%d")
                daily_dir = self.storage_path / date_str
                
                if daily_dir.exists():
                    # Get all metrics files for this day
                    json_files = list(daily_dir.glob("metrics_*.json"))
                    gz_files = list(daily_dir.glob("metrics_*.json.gz"))
                    
                    # Process uncompressed files
                    for file_path in json_files:
                        snapshot = self._load_snapshot_file(file_path)
                        if snapshot and self._is_in_time_range(snapshot, start_time, end_time):
                            snapshots.append(snapshot)
                    
                    # Process compressed files
                    for file_path in gz_files:
                        snapshot = self._load_compressed_snapshot_file(file_path)
                        if snapshot and self._is_in_time_range(snapshot, start_time, end_time):
                            snapshots.append(snapshot)
                
                current_date += timedelta(days=1)
            
            # Sort by timestamp
            snapshots.sort(key=lambda x: x.timestamp)
            
            # Apply limit
            if limit:
                snapshots = snapshots[-limit:]
            
        except Exception as e:
            logger.error(f"Error retrieving file snapshots: {e}")
            
        return snapshots
    
    def _load_snapshot_file(self, file_path: Path) -> Optional[MetricsSnapshot]:
        """Load a single snapshot from JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return self._dict_to_snapshot(data)
        except Exception as e:
            logger.error(f"Error loading snapshot from {file_path}: {e}")
            return None
    
    def _load_compressed_snapshot_file(self, file_path: Path) -> Optional[MetricsSnapshot]:
        """Load a compressed snapshot file."""
        try:
            with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
            return self._dict_to_snapshot(data)
        except Exception as e:
            logger.error(f"Error loading compressed snapshot from {file_path}: {e}")
            return None
    
    def _is_in_time_range(self, snapshot: MetricsSnapshot, 
                         start_time: datetime, end_time: datetime) -> bool:
        """Check if snapshot is within time range."""
        return start_time <= snapshot.timestamp <= end_time
    
    def export_to_json(self, output_path: str, start_time: Optional[datetime] = None,
                      end_time: Optional[datetime] = None) -> bool:
        """Export metrics to JSON file."""
        try:
            snapshots = self.get_snapshots(start_time, end_time)
            
            data = {
                'export_info': {
                    'start_time': start_time.isoformat() if start_time else None,
                    'end_time': end_time.isoformat() if end_time else None,
                    'snapshot_count': len(snapshots),
                    'export_timestamp': datetime.now().isoformat()
                },
                'snapshots': [self._snapshot_to_dict(snapshot) for snapshot in snapshots]
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Exported {len(snapshots)} snapshots to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting to JSON: {e}")
            return False
    
    def export_to_csv(self, output_path: str, start_time: Optional[datetime] = None,
                     end_time: Optional[datetime] = None) -> bool:
        """Export metrics to CSV file."""
        try:
            snapshots = self.get_snapshots(start_time, end_time)
            
            if not snapshots:
                logger.warning("No snapshots to export")
                return False
            
            # Prepare CSV data
            csv_data = []
            headers = [
                'timestamp', 'active_connections', 'total_connections',
                'request_count', 'request_rate', 'response_time_avg',
                'cpu_usage_percent', 'memory_usage_percent',
                'events_sent', 'events_received', 'tool_calls_total',
                'uptime_seconds', 'error_count_total'
            ]
            
            for snapshot in snapshots:
                row = [
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
                ]
                csv_data.append(row)
            
            # Write CSV file
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(csv_data)
            
            logger.info(f"Exported {len(snapshots)} snapshots to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return False
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        try:
            total_files = 0
            total_size = 0
            date_directories = []
            
            for item in self.storage_path.iterdir():
                if item.is_dir():
                    try:
                        datetime.strptime(item.name, "%Y%m%d")
                        date_directories.append(item.name)
                        
                        # Count files and size in this directory
                        for file_item in item.iterdir():
                            if file_item.is_file():
                                total_files += 1
                                total_size += file_item.stat().st_size
                    except ValueError:
                        continue
            
            return {
                'storage_backend': self.storage_backend,
                'storage_path': str(self.storage_path),
                'retention_hours': self.retention_hours,
                'compression_enabled': self.compression_enabled,
                'date_directories': len(date_directories),
                'total_files': total_files,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {}
    
    def cleanup_storage(self) -> bool:
        """Clean up storage by removing old files and compressing large directories."""
        try:
            self._cleanup_old_files()
            
            # Compress large directories
            for item in self.storage_path.iterdir():
                if item.is_dir():
                    self._check_compression(item)
            
            logger.info("Storage cleanup completed")
            return True
            
        except Exception as e:
            logger.error(f"Error during storage cleanup: {e}")
            return False