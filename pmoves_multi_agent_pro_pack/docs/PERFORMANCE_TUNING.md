# Performance Tuning Guide for Docling MCP Server

This comprehensive guide provides performance optimization strategies and tuning recommendations for the Docling MCP Server across different deployment scenarios and use cases.

## Table of Contents

1. [Overview](#overview)
2. [Performance Architecture](#performance-architecture)
3. [SSE Handler Optimization](#sse-handler-optimization)
4. [Memory Management](#memory-management)
5. [CPU Optimization](#cpu-optimization)
6. [Network Performance](#network-performance)
7. [Document Processing Optimization](#document-processing-optimization)
8. [Container Performance](#container-performance)
9. [Scenario-Specific Tuning](#scenario-specific-tuning)
10. [Benchmarking Procedures](#benchmarking-procedures)
11. [Configuration Optimization](#configuration-optimization)
12. [Tools and Utilities](#tools-and-utilities)
13. [Troubleshooting Performance Issues](#troubleshooting-performance-issues)

## Overview

The Docling MCP Server is designed for high-performance document processing with configurable optimization parameters. This guide covers all aspects of performance tuning to help you achieve optimal performance for your specific deployment scenario.

### Key Performance Components

- **SSE Handler**: Manages real-time communication streams
- **Document Processing Pipeline**: Docling-based document conversion
- **Metrics Collection**: Performance monitoring and alerting
- **Configuration System**: Environment-specific optimization
- **Resource Management**: Memory, CPU, and network optimization

## Performance Architecture

### Core Performance Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Performance Layer                        │
├─────────────────────────────────────────────────────────────┤
│  SSE Handler  │  Document Processing  │  Metrics System    │
│  - Queues     │  - Docling Pipeline   │  - Collection      │
│  - Streams    │  - Cache Management   │  - Storage         │
│  - Keepalive  │  - Batch Processing   │  - Alerting        │
├─────────────────────────────────────────────────────────────┤
│                    Resource Layer                           │
│  Memory Management  │  CPU Optimization  │  Network I/O     │
├─────────────────────────────────────────────────────────────┤
│                   Infrastructure Layer                      │
│  Container Runtime  │  Storage Systems  │  Load Balancer    │
└─────────────────────────────────────────────────────────────┘
```

### Performance Bottlenecks

Common performance bottlenecks in the Docling MCP Server:

1. **SSE Queue Saturation**: High event volume overwhelming queue buffers
2. **Memory Pressure**: Large document processing consuming excessive memory
3. **CPU Contention**: Complex document processing causing CPU spikes
4. **Network Latency**: Slow client connections affecting SSE streams
5. **Disk I/O**: Cache operations and temporary file processing
6. **Garbage Collection**: Python GC pauses during high load

## SSE Handler Optimization

The Server-Sent Events (SSE) handler is critical for real-time communication performance.

### Queue Management

#### Configuration Parameters

```yaml
sse:
  endpoint: "/mcp"
  keepalive_interval: 0.1  # seconds (tune based on network conditions)
  connection_timeout: 30.0  # seconds
  max_queue_size: 1000     # Increase for high-throughput scenarios
  cors_origins: ["*"]      # Restrict in production for security
  cors_methods: ["GET", "OPTIONS"]
  cors_headers: ["Content-Type", "Accept", "Cache-Control"]
  cors_max_age: 86400      # 24 hours
```

#### Optimization Strategies

**High-Throughput Scenarios**:
```yaml
# For high-volume event streaming
sse:
  keepalive_interval: 0.05   # Faster keepalive for better responsiveness
  max_queue_size: 5000       # Larger queue for burst handling
  connection_timeout: 60.0   # Longer timeout for slow clients
```

**Low-Latency Scenarios**:
```yaml
# For minimal latency requirements
sse:
  keepalive_interval: 0.01   # Very frequent keepalive
  max_queue_size: 500        # Smaller queue for faster processing
  connection_timeout: 10.0   # Shorter timeout for quick cleanup
```

### Connection Management

#### Connection Pooling

The SSE handler uses asyncio queues for connection management. Optimize based on expected concurrent connections:

```python
# In docling_mcp_server.py - optimize queue sizes
client_to_server_queue: asyncio.Queue[Any] = Queue(maxsize=2000)  # Increase for high concurrency
server_to_client_queue: asyncio.Queue[Any] = Queue(maxsize=2000)  # Match input queue size
```

#### Connection Lifecycle Optimization

```python
# Optimize connection cleanup and resource management
async def custom_sse_handler(request: Request) -> StreamResponse:
    # Implement connection limiting
    if len(server._active_connections) >= config.performance.max_connections:
        return web.Response(status=503, text="Service temporarily unavailable")
    
    # Optimize connection tracking
    connection_id = f"{request.remote}_{id(request)}"
    start_time = time.time()
    
    try:
        # Connection handling logic
        pass
    finally:
        # Ensure proper cleanup
        duration = time.time() - start_time
        server.metrics_collector.record_connection_end(connection_id, duration=duration)
```

### Event Processing Optimization

#### Batch Event Processing

```python
# Implement batch processing for high-volume scenarios
async def process_events_batch(events: List[Any], batch_size: int = 100):
    """Process multiple events in batches for better throughput."""
    for i in range(0, len(events), batch_size):
        batch = events[i:i + batch_size]
        await asyncio.gather(*[process_single_event(event) for event in batch])
```

#### Event Compression

```python
# Enable event compression for large payloads
async def send_compressed_event(response: StreamResponse, data: Any):
    """Send compressed SSE events for large payloads."""
    import gzip
    import json
    
    json_data = json.dumps(data)
    if len(json_data) > 1024:  # Compress events larger than 1KB
        compressed = gzip.compress(json_data.encode('utf-8'))
        sse_data = f"data: {compressed}\n\n"
        await response.write(sse_data)
    else:
        sse_data = f"data: {json_data}\n\n"
        await response.write(sse_data.encode('utf-8'))
```

## Memory Management

Effective memory management is crucial for stable performance, especially when processing large documents.

### Memory Configuration

#### Basic Memory Settings

```yaml
performance:
  tool_timeout: 30.0        # Tool execution timeout
  max_connections: 100      # Maximum concurrent connections
  rate_limit_requests: 1000  # Rate limiting
  rate_limit_window: 3600   # Rate limit window (seconds)

docling:
  enable_cache: true
  cache_dir: "/data/cache"
  max_file_size: 104857600  # 100MB maximum file size
```

#### Advanced Memory Optimization

```yaml
# For memory-constrained environments
performance:
  max_connections: 50       # Reduce concurrent connections
  tool_timeout: 15.0        # Shorter timeouts

docling:
  max_file_size: 52428800   # 50MB limit for memory efficiency
  enable_cache: true
  cache_dir: "/tmp/cache"   # Use faster storage for cache

metrics:
  collection_interval: 30.0  # Less frequent collection
  retention_hours: 12       # Shorter retention
  storage_backend: "file"   # Use file storage to reduce memory usage
```

### Memory Profiling and Monitoring

#### Memory Usage Tracking

```python
# Add memory monitoring to identify leaks
import psutil
import gc

def monitor_memory_usage():
    """Monitor memory usage and detect leaks."""
    process = psutil.Process()
    memory_info = process.memory_info()
    
    # Log memory usage
    logger.info(f"Memory usage: RSS={memory_info.rss/1024/1024:.2f}MB, "
                f"VMS={memory_info.vms/1024/1024:.2f}MB")
    
    # Force garbage collection if memory is high
    if memory_info.rss > 1024 * 1024 * 1024:  # 1GB threshold
        gc.collect()
        logger.info("Forced garbage collection due to high memory usage")
```

#### Memory Leak Detection

```python
# Implement memory leak detection
import tracemalloc

def start_memory_tracking():
    """Start memory tracking for leak detection."""
    tracemalloc.start()
    logger.info("Memory tracking started")

def check_memory_leaks():
    """Check for memory leaks."""
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')
    
    for stat in top_stats[:10]:
        logger.info(f"Memory leak detected: {stat}")
```

### Caching Strategies

#### Document Cache Optimization

```python
# Optimize document caching for better memory usage
from functools import lru_cache
import hashlib

class DocumentCache:
    def __init__(self, max_size: int = 100, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self.cache = {}
        self.access_times = {}
    
    @lru_cache(maxsize=50)
    def get_document_hash(self, file_path: str) -> str:
        """Get document hash for cache key."""
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def get_cached_result(self, file_path: str, output_format: str):
        """Get cached document processing result."""
        cache_key = f"{self.get_document_hash(file_path)}_{output_format}"
        
        if cache_key in self.cache:
            cached_time, result = self.cache[cache_key]
            if time.time() - cached_time < self.ttl:
                self.access_times[cache_key] = time.time()
                return result
            else:
                del self.cache[cache_key]
                del self.access_times[cache_key]
        
        return None
```

#### Cache Eviction Policies

```python
# Implement LRU cache eviction
def evict_old_cache_entries(self):
    """Evict old cache entries based on LRU policy."""
    if len(self.cache) >= self.max_size:
        # Sort by access time and remove oldest entries
        sorted_entries = sorted(self.access_times.items(), key=lambda x: x[1])
        entries_to_remove = sorted_entries[:len(self.cache) - self.max_size + 1]
        
        for cache_key, _ in entries_to_remove:
            if cache_key in self.cache:
                del self.cache[cache_key]
            del self.access_times[cache_key]
```

## CPU Optimization

CPU optimization focuses on efficient processing of document conversion requests and managing computational resources.

### Thread Management

#### Async Task Optimization

```python
# Optimize async task management for better CPU utilization
import asyncio
from concurrent.futures import ThreadPoolExecutor

class CPUOptimizedProcessor:
    def __init__(self, max_workers: int = None):
        # Use number of CPU cores for optimal performance
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
    
    async def process_document_cpu_intensive(self, file_path: str) -> Any:
        """Process document in thread pool for CPU-intensive operations."""
        loop = asyncio.get_event_loop()
        
        # Run CPU-intensive operations in thread pool
        result = await loop.run_in_executor(
            self.executor,
            self._convert_document_sync,
            file_path
        )
        
        return result
    
    def _convert_document_sync(self, file_path: str) -> Any:
        """Synchronous document conversion for thread pool."""
        converter = DocumentConverter()
        return converter.convert(file_path)
```

#### Worker Pool Configuration

```yaml
# Configure worker pools for different scenarios
performance:
  # High-performance scenario
  cpu_workers: 8              # Number of CPU workers
  io_workers: 16              # Number of I/O workers
  batch_size: 10              # Batch processing size
  
  # Resource-constrained scenario
  cpu_workers: 2              # Fewer CPU workers
  io_workers: 4               # Fewer I/O workers
  batch_size: 5               # Smaller batch size
```

### Async Operation Tuning

#### Event Loop Optimization

```python
# Optimize event loop for better performance
import asyncio

def optimize_event_loop():
    """Optimize asyncio event loop for better performance."""
    # Set event loop policy for better I/O performance
    if sys.platform == 'linux':
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    
    # Configure event loop parameters
    loop = asyncio.get_event_loop()
    
    # Optimize for high concurrency
    if hasattr(loop, 'set_debug'):
        loop.set_debug(False)  # Disable debug in production
    
    return loop
```

#### Coroutine Management

```python
# Implement efficient coroutine management
class CoroutineManager:
    def __init__(self, max_concurrent: int = 100):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_tasks = set()
    
    async def execute_with_limit(self, coro):
        """Execute coroutine with concurrency limit."""
        async with self.semaphore:
            task = asyncio.create_task(coro)
            self.active_tasks.add(task)
            task.add_done_callback(self.active_tasks.discard)
            return await task
    
    async def wait_for_completion(self):
        """Wait for all active tasks to complete."""
        if self.active_tasks:
            await asyncio.gather(*self.active_tasks, return_exceptions=True)
```

### Resource Utilization

#### CPU Affinity and Priority

```python
# Set CPU affinity for better performance
import psutil

def set_cpu_affinity(process_id: int, cpu_cores: List[int]):
    """Set CPU affinity for process."""
    try:
        p = psutil.Process(process_id)
        p.cpu_affinity(cpu_cores)
        logger.info(f"Set CPU affinity to cores: {cpu_cores}")
    except Exception as e:
        logger.warning(f"Failed to set CPU affinity: {e}")

def set_process_priority(process_id: int, priority: int):
    """Set process priority for better performance."""
    try:
        p = psutil.Process(process_id)
        if sys.platform == 'win32':
            p.nice(priority)  # Windows priority
        else:
            p.nice(priority)  # Unix nice value
        logger.info(f"Set process priority to: {priority}")
    except Exception as e:
        logger.warning(f"Failed to set process priority: {e}")
```

#### Load Balancing

```python
# Implement load balancing for document processing
class LoadBalancer:
    def __init__(self, workers: List[str]):
        self.workers = workers
        self.current_worker = 0
        self.worker_load = {worker: 0 for worker in workers}
    
    def get_next_worker(self) -> str:
        """Get next worker based on load."""
        # Find worker with minimum load
        min_load_worker = min(self.worker_load.items(), key=lambda x: x[1])
        self.worker_load[min_load_worker[0]] += 1
        return min_load_worker[0]
    
    def release_worker(self, worker: str):
        """Release worker after task completion."""
        if worker in self.worker_load:
            self.worker_load[worker] = max(0, self.worker_load[worker] - 1)
```

## Network Performance

Network optimization focuses on efficient data transfer, connection management, and latency reduction.

### Connection Pooling

#### HTTP Connection Optimization

```python
# Optimize HTTP connections for better performance
import aiohttp
from aiohttp import TCPConnector

class OptimizedHTTPClient:
    def __init__(self):
        # Configure connection pool for optimal performance
        self.connector = TCPConnector(
            limit=100,              # Total connection pool size
            limit_per_host=20,      # Connections per host
            ttl_dns_cache=300,       # DNS cache TTL
            use_dns_cache=True,      # Enable DNS caching
            keepalive_timeout=30,    # Keep-alive timeout
            enable_cleanup_closed=True  # Enable cleanup of closed connections
        )
        
        # Configure session timeouts
        self.timeout = aiohttp.ClientTimeout(
            total=60,               # Total timeout
            connect=10,             # Connection timeout
            sock_read=30            # Socket read timeout
        )
    
    async def create_session(self) -> aiohttp.ClientSession:
        """Create optimized HTTP session."""
        return aiohttp.ClientSession(
            connector=self.connector,
            timeout=self.timeout,
            headers={
                'Connection': 'keep-alive',
                'Keep-Alive': 'timeout=30, max=100'
            }
        )
```

#### Connection Reuse

```python
# Implement connection reuse for better performance
class ConnectionPool:
    def __init__(self, max_connections: int = 50):
        self.max_connections = max_connections
        self.connections = {}
        self.connection_usage = {}
    
    async def get_connection(self, host: str, port: int):
        """Get or create connection."""
        connection_key = f"{host}:{port}"
        
        if connection_key in self.connections:
            # Reuse existing connection
            connection = self.connections[connection_key]
            self.connection_usage[connection_key] += 1
            return connection
        else:
            # Create new connection
            if len(self.connections) >= self.max_connections:
                # Remove least used connection
                least_used = min(self.connection_usage.items(), key=lambda x: x[1])
                del self.connections[least_used[0]]
                del self.connection_usage[least_used[0]]
            
            connection = await self._create_connection(host, port)
            self.connections[connection_key] = connection
            self.connection_usage[connection_key] = 1
            return connection
```

### Bandwidth Optimization

#### Data Compression

```python
# Implement data compression for network transfer
import gzip
import zlib

class NetworkOptimizer:
    @staticmethod
    async def compress_data(data: bytes, algorithm: str = 'gzip') -> bytes:
        """Compress data for network transfer."""
        if algorithm == 'gzip':
            return gzip.compress(data, compresslevel=6)
        elif algorithm == 'zlib':
            return zlib.compress(data, level=6)
        else:
            return data
    
    @staticmethod
    async def decompress_data(data: bytes, algorithm: str = 'gzip') -> bytes:
        """Decompress received data."""
        if algorithm == 'gzip':
            return gzip.decompress(data)
        elif algorithm == 'zlib':
            return zlib.decompress(data)
        else:
            return data
    
    @staticmethod
    def should_compress(data: bytes, min_size: int = 1024) -> bool:
        """Determine if data should be compressed."""
        return len(data) >= min_size
```

#### Chunked Transfer

```python
# Implement chunked transfer for large files
class ChunkedTransfer:
    def __init__(self, chunk_size: int = 8192):
        self.chunk_size = chunk_size
    
    async def send_chunked_data(self, response: StreamResponse, data: bytes):
        """Send data in chunks for better memory usage."""
        total_size = len(data)
        bytes_sent = 0
        
        while bytes_sent < total_size:
            chunk = data[bytes_sent:bytes_sent + self.chunk_size]
            await response.write(chunk)
            bytes_sent += len(chunk)
            
            # Yield control to event loop
            await asyncio.sleep(0)
    
    async def receive_chunked_data(self, request: Request) -> bytes:
        """Receive chunked data efficiently."""
        chunks = []
        async for chunk in request.content.iter_chunked(self.chunk_size):
            chunks.append(chunk)
        
        return b''.join(chunks)
```

### Latency Reduction

#### Connection Pre-warming

```python
# Implement connection pre-warming for reduced latency
class ConnectionWarmer:
    def __init__(self, targets: List[Dict[str, Any]]):
        self.targets = targets
        self.warmed_connections = {}
    
    async def warm_connections(self):
        """Pre-warm connections to reduce latency."""
        tasks = []
        for target in self.targets:
            task = asyncio.create_task(self._warm_single_connection(target))
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _warm_single_connection(self, target: Dict[str, Any]):
        """Warm single connection."""
        try:
            host = target['host']
            port = target['port']
            
            # Create and test connection
            reader, writer = await asyncio.open_connection(host, port)
            self.warmed_connections[f"{host}:{port}"] = (reader, writer)
            
            logger.info(f"Warmed connection to {host}:{port}")
        except Exception as e:
            logger.warning(f"Failed to warm connection to {target}: {e}")
```

#### Request Batching

```python
# Implement request batching for reduced overhead
class RequestBatcher:
    def __init__(self, batch_size: int = 10, batch_timeout: float = 0.1):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.pending_requests = []
        self.batch_timer = None
    
    async def add_request(self, request: Dict[str, Any]) -> Any:
        """Add request to batch."""
        future = asyncio.Future()
        self.pending_requests.append((request, future))
        
        if len(self.pending_requests) >= self.batch_size:
            await self._process_batch()
        elif self.batch_timer is None:
            self.batch_timer = asyncio.create_task(self._batch_timeout())
        
        return await future
    
    async def _batch_timeout(self):
        """Process batch on timeout."""
        await asyncio.sleep(self.batch_timeout)
        if self.pending_requests:
            await self._process_batch()
    
    async def _process_batch(self):
        """Process batch of requests."""
        if not self.pending_requests:
            return
        
        if self.batch_timer:
            self.batch_timer.cancel()
            self.batch_timer = None
        
        batch = self.pending_requests.copy()
        self.pending_requests.clear()
        
        # Process batch
        requests = [req for req, _ in batch]
        futures = [fut for _, fut in batch]
        
        try:
            results = await self._execute_batch(requests)
            for future, result in zip(futures, results):
                if not future.done():
                    future.set_result(result)
        except Exception as e:
            for future in futures:
                if not future.done():
                    future.set_exception(e)
```

## Document Processing Optimization

Document processing is the core functionality of the Docling MCP Server. Optimizing this component is crucial for overall performance.

### Docling Pipeline Optimization

#### Pipeline Configuration

```yaml
docling:
  enable_cache: true
  cache_dir: "/data/cache"
  max_file_size: 104857600  # 100MB
  
  # Pipeline optimization settings
  pipeline_options:
    # OCR optimization
    ocr_engine: "tesseract"  # or "easyocr", "paddleocr"
    ocr_languages: ["eng"]    # Limit languages for better performance
    ocr_confidence_threshold: 0.7
    
    # Image processing
    image_dpi: 300           # Optimize DPI for quality vs. speed
    image_quality: 85         # JPEG quality for compression
    
    # Text extraction
    preserve_layout: true    # Layout preservation (performance impact)
    extract_tables: true     # Table extraction (performance impact)
    extract_images: false    # Image extraction (performance impact)
```

#### Custom Pipeline Optimization

```python
# Implement custom Docling pipeline optimization
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PipelineOptions

class OptimizedDocumentConverter:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.converter = self._create_optimized_converter()
    
    def _create_optimized_converter(self) -> DocumentConverter:
        """Create optimized document converter."""
        # Configure pipeline options for performance
        pipeline_options = PipelineOptions()
        
        # Optimize OCR settings
        if 'ocr_engine' in self.config:
            pipeline_options.ocr_options = {
                'engine': self.config['ocr_engine'],
                'languages': self.config.get('ocr_languages', ['eng']),
                'confidence_threshold': self.config.get('ocr_confidence_threshold', 0.7)
            }
        
        # Optimize image processing
        if 'image_dpi' in self.config:
            pipeline_options.image_options = {
                'dpi': self.config['image_dpi'],
                'quality': self.config.get('image_quality', 85)
            }
        
        # Create converter with optimized options
        return DocumentConverter(pipeline_options=pipeline_options)
    
    async def convert_document_optimized(self, file_path: str) -> Any:
        """Convert document with performance optimizations."""
        # Pre-check file size
        file_size = os.path.getsize(file_path)
        if file_size > self.config.get('max_file_size', 104857600):
            raise ValueError(f"File too large: {file_size} bytes")
        
        # Convert with timeout
        try:
            result = await asyncio.wait_for(
                self._convert_in_thread_pool(file_path),
                timeout=self.config.get('conversion_timeout', 30.0)
            )
            return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"Document conversion timed out: {file_path}")
    
    async def _convert_in_thread_pool(self, file_path: str) -> Any:
        """Convert document in thread pool to avoid blocking."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.converter.convert, file_path)
```

### Batch Processing

#### Efficient Batch Processing

```python
# Implement efficient batch processing
class BatchDocumentProcessor:
    def __init__(self, batch_size: int = 10, max_workers: int = 4):
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.converter = OptimizedDocumentConverter({})
    
    async def process_batch(self, file_paths: List[str]) -> List[Any]:
        """Process multiple documents in batch."""
        results = []
        
        # Process in batches to manage memory usage
        for i in range(0, len(file_paths), self.batch_size):
            batch = file_paths[i:i + self.batch_size]
            
            # Process batch concurrently
            tasks = [
                self.converter.convert_document_optimized(file_path)
                for file_path in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(batch_results)
            
            # Allow garbage collection between batches
            await asyncio.sleep(0.01)
        
        return results
    
    async def process_batch_with_progress(self, file_paths: List[str], 
                                       progress_callback: Callable = None) -> List[Any]:
        """Process batch with progress reporting."""
        results = []
        total_files = len(file_paths)
        processed_files = 0
        
        for i in range(0, len(file_paths), self.batch_size):
            batch = file_paths[i:i + self.batch_size]
            
            tasks = [
                self.converter.convert_document_optimized(file_path)
                for file_path in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(batch_results)
            
            processed_files += len(batch)
            
            if progress_callback:
                progress = (processed_files / total_files) * 100
                await progress_callback(progress, processed_files, total_files)
        
        return results
```

#### Memory-Efficient Processing

```python
# Implement memory-efficient document processing
class MemoryEfficientProcessor:
    def __init__(self, max_memory_mb: int = 1024):
        self.max_memory_mb = max_memory_mb
        self.current_memory_mb = 0
    
    async def process_document_streaming(self, file_path: str) -> Any:
        """Process document with streaming to reduce memory usage."""
        # Check memory availability
        if self.current_memory_mb > self.max_memory_mb * 0.8:
            await self._cleanup_memory()
        
        # Process document in chunks if large
        file_size = os.path.getsize(file_path)
        if file_size > 50 * 1024 * 1024:  # 50MB threshold
            return await self._process_large_document(file_path)
        else:
            return await self._process_regular_document(file_path)
    
    async def _process_large_document(self, file_path: str) -> Any:
        """Process large document in chunks."""
        # Implement chunked processing for large documents
        # This would require custom implementation based on document type
        pass
    
    async def _cleanup_memory(self):
        """Clean up memory to prevent OOM."""
        import gc
        gc.collect()
        
        # Clear caches if needed
        if hasattr(self, 'converter'):
            self.converter.clear_cache()
        
        self.current_memory_mb = self._get_memory_usage()
    
    def _get_memory_usage(self) -> int:
        """Get current memory usage in MB."""
        import psutil
        process = psutil.Process()
        return process.memory_info().rss // 1024 // 1024
```

### File I/O Optimization

#### Efficient File Handling

```python
# Implement efficient file I/O operations
import aiofiles
from pathlib import Path

class OptimizedFileHandler:
    def __init__(self, buffer_size: int = 8192):
        self.buffer_size = buffer_size
    
    async def read_file_optimized(self, file_path: str) -> bytes:
        """Read file with optimized buffering."""
        async with aiofiles.open(file_path, 'rb') as file:
            chunks = []
            while True:
                chunk = await file.read(self.buffer_size)
                if not chunk:
                    break
                chunks.append(chunk)
            
            return b''.join(chunks)
    
    async def write_file_optimized(self, file_path: str, data: bytes):
        """Write file with optimized buffering."""
        async with aiofiles.open(file_path, 'wb') as file:
            for i in range(0, len(data), self.buffer_size):
                chunk = data[i:i + self.buffer_size]
                await file.write(chunk)
    
    async def copy_file_optimized(self, source: str, destination: str):
        """Copy file with optimized streaming."""
        async with aiofiles.open(source, 'rb') as src_file:
            async with aiofiles.open(destination, 'wb') as dst_file:
                while True:
                    chunk = await src_file.read(self.buffer_size)
                    if not chunk:
                        break
                    await dst_file.write(chunk)
```

#### Temporary File Management

```python
# Implement efficient temporary file management
import tempfile
import shutil
from pathlib import Path

class TempFileManager:
    def __init__(self, temp_dir: str = None):
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.temp_files = set()
    
    def create_temp_file(self, suffix: str = '.tmp') -> str:
        """Create temporary file with tracking."""
        temp_file = tempfile.NamedTemporaryFile(
            dir=self.temp_dir,
            suffix=suffix,
            delete=False
        )
        self.temp_files.add(temp_file.name)
        return temp_file.name
    
    async def cleanup_temp_files(self):
        """Clean up all temporary files."""
        for temp_file in self.temp_files.copy():
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                self.temp_files.remove(temp_file)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")
    
    def __del__(self):
        """Cleanup on object destruction."""
        if self.temp_files:
            asyncio.create_task(self.cleanup_temp_files())
```

## Container Performance

Container optimization focuses on Docker configuration, resource limits, and orchestration for optimal performance.

### Docker Optimization

#### Multi-stage Build Optimization

```dockerfile
# Dockerfile.docling-mcp - Optimized for performance
FROM python:3.11-slim-bullseye as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY docling_mcp_requirements.txt .
RUN pip install --no-cache-dir --user -r docling_mcp_requirements.txt

# Production stage
FROM python:3.11-slim-bullseye

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Set PATH for user-installed packages
ENV PATH=/root/.local/bin:$PATH

# Create app user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser . .

# Create necessary directories
RUN mkdir -p /data/cache /var/log

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f -H "Accept: text/event-stream" http://localhost:3020/health || exit 1

# Expose port
EXPOSE 3020

# Performance optimizations
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONOPTIMIZE=1

# Start application
CMD ["python", "docling_mcp_server.py", "--environment", "production"]
```

#### Resource Limits and Configuration

```yaml
# docker-compose.mcp-pro.yml - Performance optimized
version: '3.8'

services:
  docling-mcp:
    build:
      context: .
      dockerfile: Dockerfile.docling-mcp
    working_dir: /app
    
    # Resource limits for performance optimization
    deploy:
      resources:
        limits:
          cpus: '2.0'           # CPU limit
          memory: 2G            # Memory limit
        reservations:
          cpus: '1.0'           # CPU reservation
          memory: 1G            # Memory reservation
    
    # Performance tuning
    environment:
      # Python optimizations
      PYTHONUNBUFFERED: "1"
      PYTHONDONTWRITEBYTECODE: "1"
      PYTHONOPTIMIZE: "1"
      
      # Docling optimizations
      DOCLING_MCP_DOCLING__CACHE_DIR: /data/cache
      DOCLING_MCP_DOCLING__ENABLE_CACHE: "true"
      DOCLING_MCP_DOCLING__MAX_FILE_SIZE: "52428800"  # 50MB
      
      # Performance settings
      DOCLING_MCP_PERFORMANCE__TOOL_TIMEOUT: "30.0"
      DOCLING_MCP_PERFORMANCE__MAX_CONNECTIONS: "200"
      
      # Metrics optimization
      DOCLING_MCP_METRICS__COLLECTION_INTERVAL: "30.0"
      DOCLING_MCP_METRICS__RETENTION_HOURS: "168"
      DOCLING_MCP_METRICS__STORAGE_BACKEND: "file"
    
    volumes:
      - ./data/docling:/data
      - ./config:/app/config:ro
      - docling_logs:/var/log
    
    ports:
      - "3020:3020"
    
    restart: unless-stopped
    
    # Health check optimization
    healthcheck:
      test: ["CMD", "curl", "-H", "Accept: text/event-stream", "-f", "http://localhost:3020/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
```

### Container Resource Management

#### Memory and CPU Optimization

```yaml
# Production resource configuration
services:
  docling-mcp:
    # High-performance configuration
    deploy:
      resources:
        limits:
          cpus: '4.0'           # 4 CPU cores
          memory: 4G            # 4GB RAM
        reservations:
          cpus: '2.0'           # 2 CPU cores guaranteed
          memory: 2G            # 2GB RAM guaranteed
    
    # JVM-style tuning for Python
    environment:
      # Memory optimization
      MALLOC_ARENA_MAX: "2"    # Reduce memory fragmentation
      PYTHONMALLOC: "malloc"   # Use malloc for better performance
      
      # CPU optimization
      OMP_NUM_THREADS: "4"     # OpenMP threads
      NUMBA_NUM_THREADS: "4"   # Numba threads
      
      # I/O optimization
      AIOFILES_THREADS: "8"    # Async file I/O threads
```

#### Storage Optimization

```yaml
# Storage performance optimization
services:
  docling-mcp:
    volumes:
      # Use tmpfs for high-performance cache
      - type: tmpfs
        target: /tmp/cache
        tmpfs:
          size: 1G
          mode: 1777
      
      # Use volume for persistent data
      - docling_data:/data
      - docling_cache:/data/cache
    
    # Storage driver optimization
    environment:
      DOCLING_MCP_DOCLING__CACHE_DIR: /data/cache
      DOCLING_MCP_DOCLING__TEMP_DIR: /tmp/cache

volumes:
  docling_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/docling/data
  
  docling_cache:
    driver: local
    driver_opts:
      type: tmpfs
      device: tmpfs
      o: size=2G,uid=1000,gid=1000
```

### Orchestration Performance

#### Kubernetes Optimization

```yaml
# kubernetes-deployment.yaml - Performance optimized
apiVersion: apps/v1
kind: Deployment
metadata:
  name: docling-mcp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: docling-mcp
  template:
    metadata:
      labels:
        app: docling-mcp
    spec:
      containers:
      - name: docling-mcp
        image: docling-mcp:latest
        
        # Resource requests and limits
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        
        # Performance environment variables
        env:
        - name: DOCLING_MCP_PERFORMANCE__MAX_CONNECTIONS
          value: "500"
        - name: DOCLING_MCP_METRICS__COLLECTION_INTERVAL
          value: "15.0"
        - name: PYTHONUNBUFFERED
          value: "1"
        
        # Liveness and readiness probes
        livenessProbe:
          httpGet:
            path: /health
            port: 3020
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        
        readinessProbe:
          httpGet:
            path: /health
            port: 3020
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2
        
        # Volume mounts
        volumeMounts:
        - name: cache-volume
          mountPath: /data/cache
        - name: config-volume
          mountPath: /app/config
          readOnly: true
      
      volumes:
      - name: cache-volume
        emptyDir:
          sizeLimit: 1Gi
      - name: config-volume
        configMap:
          name: docling-config
      
      # Node selection for performance
      nodeSelector:
        node-type: high-performance
      
      # Affinity rules
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - docling-mcp
              topologyKey: kubernetes.io/hostname
```

#### Horizontal Pod Autoscaling

```yaml
# hpa.yaml - Auto-scaling configuration
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: docling-mcp-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: docling-mcp
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
```

## Scenario-Specific Tuning

Different deployment scenarios require different optimization strategies. This section provides scenario-specific tuning guidelines.

### Development Environment

Development environments prioritize debugging and developer experience over raw performance.

#### Configuration for Development

```yaml
# config/development.yaml - Development optimization
logging:
  level: "DEBUG"              # Verbose logging for debugging
  format: "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
  output: "stdout"

performance:
  tool_timeout: 60.0           # Longer timeout for debugging
  max_connections: 50          # Fewer connections for development
  rate_limit_requests: 1000    # Relaxed rate limiting
  rate_limit_window: 3600

security:
  enable_cors: true
  allowed_origins:
    - "http://localhost:*"
    - "https://localhost:*"
    - "http://127.0.0.1:*"
    - "https://127.0.0.1:*"
  enable_rate_limiting: false   # Disable rate limiting in development

docling:
  enable_cache: true
  cache_dir: "./data/cache"     # Local cache for development
  max_file_size: 52428800      # 50MB for development
  pipeline_options:
    preserve_layout: true      # Full feature set for development
    extract_tables: true
    extract_images: true

metrics:
  enabled: true
  collection_interval: 5.0      # Frequent collection for debugging
  retention_hours: 2           # Short retention for development
  storage_backend: "memory"    # In-memory storage for simplicity
  dashboard_enabled: true       # Enable dashboard for monitoring
```

#### Development Performance Tips

1. **Hot Reloading**: Enable hot reloading for faster development cycles
2. **Debug Mode**: Use debug mode with detailed logging
3. **Mock Services**: Use mock services for external dependencies
4. **Local Cache**: Use local cache directories for faster access
5. **Reduced Timeouts**: Use longer timeouts for debugging

```python
# Development-specific optimizations
class DevelopmentOptimizer:
    @staticmethod
    def enable_debug_mode():
        """Enable debug mode for development."""
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
        
        # Enable debug middleware
        app.middleware.insert(0, DebugMiddleware())
    
    @staticmethod
    def setup_hot_reload():
        """Setup hot reloading for development."""
        import aiohttp_debugtoolbar
        aiohttp_debugtoolbar.setup(app)
    
    @staticmethod
    def enable_profiling():
        """Enable profiling for performance analysis."""
        import cProfile
        import pstats
        
        profiler = cProfile.Profile()
        profiler.enable()
        
        # Setup profiling endpoint
        async def profiling_handler(request):
            profiler.disable()
            stats = pstats.Stats(profiler)
            stats.sort_stats('cumulative')
            return web.Response(text=stats.print_stats())
```

### Production Environment

Production environments prioritize stability, security, and performance.

#### Configuration for Production

```yaml
# config/production.yaml - Production optimization
logging:
  level: "WARNING"             # Less verbose logging
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  output: "/var/log/docling-mcp.log"  # Log to file

performance:
  tool_timeout: 30.0           # Standard timeout
  max_connections: 200         # Higher connection limit
  rate_limit_requests: 500     # Stricter rate limiting
  rate_limit_window: 3600

security:
  enable_cors: true
  # IMPORTANT: Specify actual allowed origins
  allowed_origins:
    - "https://your-domain.com"
    - "https://app.your-domain.com"
  enable_rate_limiting: true    # Enable rate limiting
  max_request_size: 52428800   # 50MB limit

docling:
  enable_cache: true
  cache_dir: "/data/cache"     # Production cache directory
  max_file_size: 52428800      # 50MB limit
  pipeline_options:
    preserve_layout: false     # Optimize for performance
    extract_tables: true
    extract_images: false       # Disable image extraction for performance

metrics:
  enabled: true
  collection_interval: 30.0    # Less frequent collection
  retention_hours: 168          # 7 days retention
  storage_backend: "file"      # Persistent storage
  storage_path: "/data/metrics"
  prometheus_enabled: true      # Enable Prometheus
  alerting_enabled: true        # Enable alerting
```

#### Production Performance Tips

1. **Connection Pooling**: Use connection pooling for database and external services
2. **Caching**: Implement multi-level caching (memory, Redis, file)
3. **Load Balancing**: Use load balancer for high availability
4. **Monitoring**: Comprehensive monitoring and alerting
5. **Security**: Implement proper security measures

```python
# Production-specific optimizations
class ProductionOptimizer:
    @staticmethod
    def setup_connection_pooling():
        """Setup connection pooling for production."""
        # Database connection pool
        engine = create_engine(
            DATABASE_URL,
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        
        # HTTP connection pool
        connector = TCPConnector(
            limit=100,
            limit_per_host=20,
            ttl_dns_cache=300,
            use_dns_cache=True
        )
    
    @staticmethod
    def setup_caching():
        """Setup multi-level caching."""
        # Redis cache for distributed caching
        redis_cache = RedisCache(
            host='redis',
            port=6379,
            db=0,
            ttl=3600
        )
        
        # Memory cache for frequently accessed data
        memory_cache = LRUCache(maxsize=1000)
        
        return CacheManager(redis_cache, memory_cache)
    
    @staticmethod
    def setup_monitoring():
        """Setup comprehensive monitoring."""
        # Prometheus metrics
        prometheus_client.start_http_server(9090)
        
        # Health checks
        health_checker = HealthChecker()
        health_checker.add_check('database', check_database)
        health_checker.add_check('redis', check_redis)
        health_checker.add_check('disk_space', check_disk_space)
```

### High-Load Scenarios

High-load scenarios require aggressive optimization and scaling strategies.

#### Configuration for High Load

```yaml
# config/high-load.yaml - High-load optimization
performance:
  tool_timeout: 15.0           # Shorter timeout for faster processing
  max_connections: 1000        # Very high connection limit
  rate_limit_requests: 5000    # High rate limit
  rate_limit_window: 3600

docling:
  enable_cache: true
  cache_dir: "/tmp/cache"      # Use fast storage for cache
  max_file_size: 104857600     # 100MB limit for batch processing
  pipeline_options:
    ocr_engine: "tesseract"    # Fastest OCR engine
    ocr_languages: ["eng"]     # Single language for speed
    preserve_layout: false      # Disable layout preservation
    extract_tables: false       # Disable table extraction
    extract_images: false       # Disable image extraction

metrics:
  enabled: true
  collection_interval: 60.0    # Less frequent to reduce overhead
  retention_hours: 24           # Shorter retention
  storage_backend: "file"      # File storage for persistence
  compression_enabled: true     # Enable compression
  compression_threshold: 100    # Compress early

# Additional high-load settings
batch_processing:
  enabled: true
  batch_size: 50               # Large batch size
  batch_timeout: 5.0            # Short batch timeout
  max_concurrent_batches: 10   # Multiple concurrent batches
```

#### High-Load Optimization Strategies

1. **Horizontal Scaling**: Deploy multiple instances behind load balancer
2. **Batch Processing**: Process documents in batches for efficiency
3. **Connection Pooling**: Aggressive connection pooling
4. **Caching**: Multi-level caching with Redis
5. **Async Processing**: Use message queues for async processing

```python
# High-load specific optimizations
class HighLoadOptimizer:
    def __init__(self):
        self.batch_processor = BatchProcessor(batch_size=50)
        self.connection_pool = ConnectionPool(max_connections=1000)
        self.cache_manager = CacheManager()
    
    async def setup_horizontal_scaling(self):
        """Setup horizontal scaling support."""
        # Redis for distributed caching
        self.redis_client = aioredis.from_url('redis://redis:6379')
        
        # Message queue for async processing
        self.message_queue = MessageQueue('redis://redis:6379/1')
        
        # Load balancer health checks
        self.health_checker = LoadBalancerHealthChecker()
    
    async def process_batch_queue(self):
        """Process documents from message queue."""
        while True:
            try:
                # Get batch from queue
                batch = await self.message_queue.get_batch(batch_size=50)
                
                if batch:
                    # Process batch concurrently
                    results = await self.batch_processor.process_batch(batch)
                    
                    # Send results back
                    await self.message_queue.send_results(results)
                
                await asyncio.sleep(0.1)  # Prevent busy waiting
                
            except Exception as e:
                logger.error(f"Batch processing error: {e}")
                await asyncio.sleep(1)  # Back off on error
    
    def setup_auto_scaling(self):
        """Setup auto-scaling based on load."""
        # Monitor queue length
        # Scale up when queue length > threshold
        # Scale down when queue length < threshold
        pass
```

### Resource-Constrained Environments

Resource-constrained environments require careful optimization to work within limited resources.

#### Configuration for Resource Constraints

```yaml
# config/resource-constrained.yaml - Resource-constrained optimization
performance:
  tool_timeout: 10.0           # Short timeout to prevent hanging
  max_connections: 20          # Very limited connections
  rate_limit_requests: 100     # Strict rate limiting
  rate_limit_window: 3600

docling:
  enable_cache: false          # Disable cache to save memory
  max_file_size: 10485760     # 10MB limit for memory efficiency
  pipeline_options:
    ocr_engine: "tesseract"   # Lightweight OCR
    ocr_languages: ["eng"]     # Single language
    preserve_layout: false     # Disable memory-intensive features
    extract_tables: false
    extract_images: false

metrics:
  enabled: false               # Disable metrics to save resources
  # If metrics are needed, use minimal configuration
  collection_interval: 300.0   # Very infrequent collection
  retention_hours: 1           # Very short retention
  storage_backend: "memory"     # In-memory only

# Resource optimization settings
memory:
  max_usage_mb: 512           # Limit memory usage
  gc_frequency: 10            # Frequent garbage collection

cpu:
  max_workers: 2              # Limit CPU workers
  batch_size: 2               # Small batch size
```

#### Resource-Constrained Optimization Strategies

1. **Memory Management**: Aggressive memory management and cleanup
2. **CPU Limiting**: Limit CPU usage to prevent overload
3. **Feature Disabling**: Disable non-essential features
4. **Lightweight Dependencies**: Use lightweight alternatives
5. **Efficient Algorithms**: Use memory-efficient algorithms

```python
# Resource-constrained specific optimizations
class ResourceConstrainedOptimizer:
    def __init__(self, max_memory_mb: int = 512):
        self.max_memory_mb = max_memory_mb
        self.memory_monitor = MemoryMonitor(max_memory_mb)
    
    async def setup_memory_management(self):
        """Setup aggressive memory management."""
        # Monitor memory usage
        asyncio.create_task(self.memory_monitor.monitor_loop())
        
        # Setup periodic cleanup
        asyncio.create_task(self.periodic_cleanup())
    
    async def periodic_cleanup(self):
        """Periodic cleanup to free memory."""
        while True:
            # Force garbage collection
            import gc
            gc.collect()
            
            # Clear caches
            if hasattr(self, 'cache'):
                self.cache.clear()
            
            # Check memory usage
            current_memory = self.memory_monitor.get_memory_usage()
            if current_memory > self.max_memory_mb * 0.8:
                await self.emergency_cleanup()
            
            await asyncio.sleep(60)  # Cleanup every minute
    
    async def emergency_cleanup(self):
        """Emergency cleanup when memory is critical."""
        logger.warning("Emergency cleanup triggered")
        
        # Clear all caches
        if hasattr(self, 'document_cache'):
            self.document_cache.clear()
        
        # Close idle connections
        if hasattr(self, 'connection_pool'):
            await self.connection_pool.close_idle_connections()
        
        # Force garbage collection multiple times
        import gc
        for _ in range(3):
            gc.collect()
            await asyncio.sleep(0.1)
    
    def optimize_document_processing(self):
        """Optimize document processing for low memory."""
        # Use streaming processing
        # Process documents in small chunks
        # Disable memory-intensive features
        pass
```

## Benchmarking Procedures

Comprehensive benchmarking is essential for understanding performance characteristics and identifying optimization opportunities.

### Performance Testing Methodology

#### Benchmark Types

1. **Load Testing**: Test system under expected load
2. **Stress Testing**: Test system beyond expected limits
3. **Endurance Testing**: Test system over extended periods
4. **Spike Testing**: Test system with sudden load spikes
5. **Volume Testing**: Test system with large data volumes

#### Benchmark Metrics

```python
# Comprehensive benchmark metrics collection
class BenchmarkMetrics:
    def __init__(self):
        self.metrics = {
            'throughput': [],           # Requests per second
            'response_time': [],        # Response times
            'error_rate': [],           # Error rates
            'cpu_usage': [],            # CPU usage
            'memory_usage': [],         # Memory usage
            'disk_io': [],              # Disk I/O
            'network_io': [],           # Network I/O
            'connection_count': [],     # Active connections
            'queue_size': [],           # Queue sizes
        }
    
    def record_metrics(self, **kwargs):
        """Record benchmark metrics."""
        for key, value in kwargs.items():
            if key in self.metrics:
                self.metrics[key].append({
                    'timestamp': time.time(),
                    'value': value
                })
    
    def get_summary_stats(self, metric_name: str) -> Dict[str, float]:
        """Get summary statistics for a metric."""
        values = [m['value'] for m in self.metrics[metric_name]]
        
        if not values:
            return {}
        
        return {
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'p50': self.percentile(values, 0.5),
            'p95': self.percentile(values, 0.95),
            'p99': self.percentile(values, 0.99),
            'count': len(values)
        }
    
    def percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile of values."""
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile)
        return sorted_values[min(index, len(sorted_values) - 1)]
```

### Load Testing Strategies

#### Concurrent User Simulation

```python
# Load testing with concurrent user simulation
import asyncio
import aiohttp
import time
from typing import List, Dict, Any

class LoadTester:
    def __init__(self, base_url: str, max_concurrent: int = 100):
        self.base_url = base_url
        self.max_concurrent = max_concurrent
        self.session = None
        self.metrics = BenchmarkMetrics()
    
    async def setup_session(self):
        """Setup HTTP session for load testing."""
        connector = aiohttp.TCPConnector(
            limit=self.max_concurrent,
            limit_per_host=self.max_concurrent,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(total=60)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )
    
    async def simulate_user(self, user_id: int, requests_per_user: int = 10) -> Dict[str, Any]:
        """Simulate a single user's activity."""
        user_metrics = {
            'user_id': user_id,
            'requests': 0,
            'errors': 0,
            'total_time': 0,
            'response_times': []
        }
        
        start_time = time.time()
        
        for i in range(requests_per_user):
            request_start = time.time()
            
            try:
                # Simulate document conversion request
                async with self.session.post(
                    f"{self.base_url}/mcp",
                    json={
                        "jsonrpc": "2.0",
                        "id": f"{user_id}-{i}",
                        "method": "tools/call",
                        "params": {
                            "name": "convert_document",
                            "arguments": {
                                "file_path": f"/test/doc_{i % 10}.pdf",
                                "output_format": "markdown"
                            }
                        }
                    }
                ) as response:
                    await response.text()
                    
                    response_time = time.time() - request_start
                    user_metrics['response_times'].append(response_time)
                    user_metrics['requests'] += 1
                    
            except Exception as e:
                user_metrics['errors'] += 1
                logger.error(f"User {user_id} request {i} failed: {e}")
            
            # Small delay between requests
            await asyncio.sleep(0.1)
        
        user_metrics['total_time'] = time.time() - start_time
        return user_metrics
    
    async def run_load_test(self, concurrent_users: int, duration: int = 60) -> Dict[str, Any]:
        """Run load test with specified concurrent users."""
        logger.info(f"Starting load test with {concurrent_users} concurrent users")
        
        # Start system monitoring
        monitor_task = asyncio.create_task(self.monitor_system())
        
        # Create user tasks
        user_tasks = []
        for i in range(concurrent_users):
            task = asyncio.create_task(
                self.simulate_user(i, requests_per_user=20)
            )
            user_tasks.append(task)
        
        # Wait for all users to complete or timeout
        try:
            user_results = await asyncio.wait_for(
                asyncio.gather(*user_tasks, return_exceptions=True),
                timeout=duration
            )
        except asyncio.TimeoutError:
            logger.warning("Load test timed out")
            for task in user_tasks:
                task.cancel()
            user_results = []
        
        # Stop monitoring
        monitor_task.cancel()
        
        # Analyze results
        return self.analyze_results(user_results)
    
    async def monitor_system(self):
        """Monitor system resources during test."""
        import psutil
        
        while True:
            try:
                # Record system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                network = psutil.net_io_counters()
                
                self.metrics.record_metrics(
                    cpu_usage=cpu_percent,
                    memory_usage=memory.percent,
                    disk_usage=disk.percent,
                    network_io=network.bytes_sent + network.bytes_recv
                )
                
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(1)
    
    def analyze_results(self, user_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze load test results."""
        total_requests = sum(r['requests'] for r in user_results if isinstance(r, dict))
        total_errors = sum(r['errors'] for r in user_results if isinstance(r, dict))
        
        all_response_times = []
        for r in user_results:
            if isinstance(r, dict):
                all_response_times.extend(r['response_times'])
        
        # Calculate statistics
        if all_response_times:
            response_time_stats = {
                'min': min(all_response_times),
                'max': max(all_response_times),
                'avg': sum(all_response_times) / len(all_response_times),
                'p50': self.percentile(all_response_times, 0.5),
                'p95': self.percentile(all_response_times, 0.95),
                'p99': self.percentile(all_response_times, 0.99),
            }
        else:
            response_time_stats = {}
        
        return {
            'total_users': len(user_results),
            'total_requests': total_requests,
            'total_errors': total_errors,
            'error_rate': (total_errors / total_requests * 100) if total_requests > 0 else 0,
            'requests_per_second': total_requests / 60,  # Assuming 60-second test
            'response_time_stats': response_time_stats,
            'system_metrics': self.metrics.get_summary_stats('cpu_usage')
        }
```

#### Stress Testing

```python
# Stress testing to find system limits
class StressTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.load_tester = LoadTester(base_url)
    
    async def find_breaking_point(self, start_users: int = 10, max_users: int = 1000) -> Dict[str, Any]:
        """Find the breaking point of the system."""
        results = []
        current_users = start_users
        
        while current_users <= max_users:
            logger.info(f"Testing with {current_users} concurrent users")
            
            try:
                result = await self.load_tester.run_load_test(
                    concurrent_users=current_users,
                    duration=30  # Shorter duration for stress testing
                )
                
                results.append({
                    'users': current_users,
                    'result': result
                })
                
                # Check if system is failing
                if result['error_rate'] > 10 or result['response_time_stats'].get('p95', 0) > 5000:
                    logger.warning(f"System showing stress at {current_users} users")
                    break
                
                # Exponential increase
                current_users = min(current_users * 2, max_users)
                
            except Exception as e:
                logger.error(f"Stress test failed at {current_users} users: {e}")
                break
        
        return {
            'test_results': results,
            'max_stable_users': self.find_max_stable_users(results),
            'breaking_point': self.find_breaking_point_users(results)
        }
    
    def find_max_stable_users(self, results: List[Dict[str, Any]]) -> int:
        """Find maximum number of users with stable performance."""
        for result in reversed(results):
            if (result['result']['error_rate'] < 5 and 
                result['result']['response_time_stats'].get('p95', 0) < 2000):
                return result['users']
        return 0
    
    def find_breaking_point_users(self, results: List[Dict[str, Any]]) -> int:
        """Find the breaking point where performance degrades significantly."""
        for i, result in enumerate(results):
            if (result['result']['error_rate'] > 10 or 
                result['result']['response_time_stats'].get('p95', 0) > 5000):
                return result['users']
        return results[-1]['users'] if results else 0
```

### Performance Profiling

#### CPU Profiling

```python
# CPU profiling for performance optimization
import cProfile
import pstats
import io
from contextlib import contextmanager

class CPUProfiler:
    def __init__(self):
        self.profiler = None
    
    @contextmanager
    def profile(self, name: str = "profile"):
        """Context manager for CPU profiling."""
        self.profiler = cProfile.Profile()
        self.profiler.enable()
        
        try:
            yield
        finally:
            self.profiler.disable()
            self.save_profile(name)
    
    def save_profile(self, name: str):
        """Save profiling results."""
        if not self.profiler:
            return
        
        # Create stats object
        s = io.StringIO()
        ps = pstats.Stats(self.profiler, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats(20)  # Top 20 functions
        
        # Save to file
        with open(f"{name}_profile.txt", 'w') as f:
            f.write(s.getvalue())
        
        # Save stats for later analysis
        ps.dump_stats(f"{name}_profile.stats")
        
        logger.info(f"Profile saved to {name}_profile.txt and {name}_profile.stats")
    
    def profile_function(self, func):
        """Decorator to profile a function."""
        def wrapper(*args, **kwargs):
            with self.profile(func.__name__):
                return func(*args, **kwargs)
        return wrapper
```

#### Memory Profiling

```python
# Memory profiling for memory optimization
import tracemalloc
import time
from typing import Dict, List

class MemoryProfiler:
    def __init__(self):
        self.snapshots = []
        self.start_time = None
    
    def start_profiling(self):
        """Start memory profiling."""
        tracemalloc.start()
        self.start_time = time.time()
        logger.info("Memory profiling started")
    
    def take_snapshot(self, label: str = ""):
        """Take a memory snapshot."""
        if not tracemalloc.is_tracing():
            logger.warning("Memory profiling not started")
            return
        
        snapshot = tracemalloc.take_snapshot()
        self.snapshots.append({
            'label': label,
            'timestamp': time.time() - self.start_time,
            'snapshot': snapshot
        })
        logger.info(f"Memory snapshot taken: {label}")
    
    def compare_snapshots(self, index1: int, index2: int) -> str:
        """Compare two memory snapshots."""
        if index1 >= len(self.snapshots) or index2 >= len(self.snapshots):
            return "Invalid snapshot indices"
        
        snapshot1 = self.snapshots[index1]['snapshot']
        snapshot2 = self.snapshots[index2]['snapshot']
        
        stats = snapshot2.compare_to(snapshot1, 'lineno')
        
        # Format comparison results
        result = []
        for stat in stats[:10]:  # Top 10 differences
            result.append(f"{stat}")
        
        return "\n".join(result)
    
    def get_memory_usage(self) -> Dict[str, int]:
        """Get current memory usage."""
        if not tracemalloc.is_tracing():
            return {}
        
        current, peak = tracemalloc.get_traced_memory()
        return {
            'current': current,
            'peak': peak,
            'current_mb': current // 1024 // 1024,
            'peak_mb': peak // 1024 // 1024
        }
    
    def stop_profiling(self):
        """Stop memory profiling and save results."""
        if not tracemalloc.is_tracing():
            return
        
        # Take final snapshot
        self.take_snapshot("final")
        
        # Save profiling results
        with open("memory_profile.txt", 'w') as f:
            f.write("Memory Profiling Results\n")
            f.write("=" * 50 + "\n\n")
            
            for i, snapshot_data in enumerate(self.snapshots):
                f.write(f"Snapshot {i}: {snapshot_data['label']}\n")
                f.write(f"Time: {snapshot_data['timestamp']:.2f}s\n")
                
                # Get top memory allocations
                stats = snapshot_data['snapshot'].statistics('lineno')
                for stat in stats[:5]:
                    f.write(f"  {stat}\n")
                f.write("\n")
        
        tracemalloc.stop()
        logger.info("Memory profiling stopped and results saved")
```

### Benchmark Automation

#### Automated Benchmark Suite

```python
# Automated benchmark suite for continuous performance testing
class BenchmarkSuite:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.load_tester = LoadTester(base_url)
        self.stress_tester = StressTester(base_url)
        self.cpu_profiler = CPUProfiler()
        self.memory_profiler = MemoryProfiler()
    
    async def run_full_benchmark(self) -> Dict[str, Any]:
        """Run comprehensive benchmark suite."""
        logger.info("Starting full benchmark suite")
        
        results = {
            'timestamp': time.time(),
            'load_tests': {},
            'stress_tests': {},
            'profiling': {},
            'recommendations': []
        }
        
        # Load testing at different scales
        load_scales = [10, 50, 100, 200]
        for scale in load_scales:
            logger.info(f"Running load test with {scale} users")
            with self.cpu_profiler.profile(f"load_test_{scale}"):
                self.memory_profiler.start_profiling()
                
                result = await self.load_tester.run_load_test(
                    concurrent_users=scale,
                    duration=60
                )
                
                self.memory_profiler.take_snapshot(f"load_test_{scale}_end")
                results['load_tests'][scale] = result
                
                self.memory_profiler.stop_profiling()
        
        # Stress testing
        logger.info("Running stress test")
        stress_result = await self.stress_tester.find_breaking_point()
        results['stress_tests'] = stress_result
        
        # Generate recommendations
        results['recommendations'] = self.generate_recommendations(results)
        
        # Save results
        self.save_benchmark_results(results)
        
        return results
    
    def generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations based on results."""
        recommendations = []
        
        # Analyze load test results
        for scale, result in results['load_tests'].items():
            if result['error_rate'] > 5:
                recommendations.append(
                    f"High error rate ({result['error_rate']:.1f}%) at {scale} users. "
                    "Consider increasing resources or optimizing code."
                )
            
            if result['response_time_stats'].get('p95', 0) > 2000:
                recommendations.append(
                    f"High response time (P95: {result['response_time_stats']['p95']:.1f}ms) "
                    f"at {scale} users. Consider performance optimizations."
                )
        
        # Analyze stress test results
        max_stable = results['stress_tests'].get('max_stable_users', 0)
        if max_stable < 100:
            recommendations.append(
                f"System becomes unstable at {max_stable} users. "
                "Consider horizontal scaling."
            )
        
        # Memory recommendations
        memory_usage = self.memory_profiler.get_memory_usage()
        if memory_usage.get('peak_mb', 0) > 1024:
            recommendations.append(
                f"High memory usage ({memory_usage['peak_mb']}MB). "
                "Consider memory optimizations."
            )
        
        return recommendations
    
    def save_benchmark_results(self, results: Dict[str, Any]):
        """Save benchmark results to file."""
        import json
        
        timestamp = int(time.time())
        filename = f"benchmark_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Benchmark results saved to {filename}")
```

## Configuration Optimization

Optimizing configuration parameters is essential for achieving optimal performance in different scenarios.

### Performance-Related Configuration

#### Core Performance Settings

```yaml
# Performance optimization configuration
performance:
  # Request processing
  tool_timeout: 30.0              # Tool execution timeout (seconds)
  max_connections: 100            # Maximum concurrent connections
  rate_limit_requests: 1000        # Rate limit requests per window
  rate_limit_window: 3600          # Rate limit window (seconds)
  
  # Batch processing
  batch_processing:
    enabled: true                   # Enable batch processing
    batch_size: 10                 # Default batch size
    batch_timeout: 5.0              # Batch timeout (seconds)
    max_concurrent_batches: 5       # Maximum concurrent batches
  
  # Connection management
  connection_pool:
    max_size: 100                  # Maximum connection pool size
    min_size: 10                   # Minimum connection pool size
    idle_timeout: 300              # Idle connection timeout (seconds)
    max_lifetime: 3600             # Connection max lifetime (seconds)
  
  # Queue management
  queue:
    max_size: 1000                 # Maximum queue size
    batch_size: 50                 # Queue batch processing size
    flush_interval: 0.1            # Queue flush interval (seconds)
```

#### SSE Performance Configuration

```yaml
# SSE performance optimization
sse:
  endpoint: "/mcp"
  keepalive_interval: 0.1          # Keepalive interval (seconds)
  connection_timeout: 30.0         # Connection timeout (seconds)
  max_queue_size: 1000            # Maximum SSE queue size
  
  # Performance tuning
  buffer_size: 8192               # Buffer size for SSE (bytes)
  compression_threshold: 1024      # Compression threshold (bytes)
  batch_events: true               # Batch SSE events
  batch_size: 10                   # SSE batch size
  batch_timeout: 0.05              # SSE batch timeout (seconds)
  
  # Connection management
  max_connections_per_client: 5    # Max connections per client
  connection_cleanup_interval: 60  # Connection cleanup interval (seconds)
  idle_connection_timeout: 300     # Idle connection timeout (seconds)
```

### Environment-Specific Tuning

#### Development Environment Tuning

```yaml
# config/development.yaml - Development optimization
logging:
  level: "DEBUG"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
  output: "stdout"

performance:
  tool_timeout: 60.0              # Longer timeout for debugging
  max_connections: 50              # Fewer connections for development
  rate_limit_requests: 1000
  rate_limit_window: 3600
  
  batch_processing:
    enabled: false                 # Disable batch processing for debugging
    batch_size: 5                  # Smaller batches
    batch_timeout: 10.0            # Longer timeout for debugging
  
  connection_pool:
    max_size: 20                   # Smaller pool for development
    min_size: 5
    idle_timeout: 60               # Shorter timeout for development

sse:
  keepalive_interval: 0.5          # Slower keepalive for debugging
  connection_timeout: 60.0         # Longer timeout for debugging
  max_queue_size: 100             # Smaller queue for development
  
  batch_events: false              # Disable batching for debugging
  compression_threshold: 512       # Lower threshold for testing

docling:
  enable_cache: true
  cache_dir: "./data/cache"
  max_file_size: 52428800         # 50MB for development
  
  pipeline_options:
    preserve_layout: true           # Full features for development
    extract_tables: true
    extract_images: true
    ocr_confidence_threshold: 0.5  # Lower threshold for testing

metrics:
  enabled: true
  collection_interval: 5.0         # Frequent collection for debugging
  retention_hours: 2               # Short retention for development
  storage_backend: "memory"        # In-memory for simplicity
  dashboard_enabled: true           # Enable dashboard
```

#### Production Environment Tuning

```yaml
# config/production.yaml - Production optimization
logging:
  level: "WARNING"                 # Less verbose logging
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  output: "/var/log/docling-mcp.log"

performance:
  tool_timeout: 30.0              # Standard timeout
  max_connections: 200             # Higher connection limit
  rate_limit_requests: 500         # Stricter rate limiting
  rate_limit_window: 3600
  
  batch_processing:
    enabled: true                   # Enable batch processing
    batch_size: 20                 # Larger batches for efficiency
    batch_timeout: 3.0             # Shorter timeout for performance
    max_concurrent_batches: 10     # More concurrent batches
  
  connection_pool:
    max_size: 100                  # Larger pool for production
    min_size: 20
    idle_timeout: 300              # Longer timeout for production
    max_lifetime: 3600

sse:
  keepalive_interval: 0.05         # Faster keepalive for responsiveness
  connection_timeout: 30.0         # Standard timeout
  max_queue_size: 2000            # Larger queue for production
  
  batch_events: true               # Enable batching for performance
  batch_size: 20                   # Larger batches
  batch_timeout: 0.02              # Shorter timeout for performance
  compression_threshold: 1024      # Standard compression threshold

docling:
  enable_cache: true
  cache_dir: "/data/cache"
  max_file_size: 52428800         # 50MB limit
  
  pipeline_options:
    preserve_layout: false          # Optimize for performance
    extract_tables: true
    extract_images: false          # Disable for performance
    ocr_confidence_threshold: 0.7  # Higher threshold for quality

metrics:
  enabled: true
  collection_interval: 30.0        # Less frequent collection
  retention_hours: 168             # 7 days retention
  storage_backend: "file"          # Persistent storage
  storage_path: "/data/metrics"
  prometheus_enabled: true         # Enable Prometheus
  alerting_enabled: true           # Enable alerting
```

#### High-Load Environment Tuning

```yaml
# config/high-load.yaml - High-load optimization
performance:
  tool_timeout: 15.0              # Shorter timeout for faster processing
  max_connections: 1000            # Very high connection limit
  rate_limit_requests: 5000        # High rate limit
  rate_limit_window: 3600
  
  batch_processing:
    enabled: true
    batch_size: 50                 # Large batches for efficiency
    batch_timeout: 2.0              # Short timeout for high throughput
    max_concurrent_batches: 20     # Many concurrent batches
  
  connection_pool:
    max_size: 500                  # Very large pool
    min_size: 50
    idle_timeout: 600              # Longer timeout for high load
    max_lifetime: 7200             # 2 hours max lifetime

sse:
  keepalive_interval: 0.01         # Very fast keepalive
  connection_timeout: 20.0         # Shorter timeout for quick cleanup
  max_queue_size: 5000            # Very large queue
  
  batch_events: true
  batch_size: 50                   # Large batches
  batch_timeout: 0.01              # Very short timeout
  compression_threshold: 512       # Lower threshold for more compression

docling:
  enable_cache: true
  cache_dir: "/tmp/cache"          # Use fast storage
  max_file_size: 104857600         # 100MB for batch processing
  
  pipeline_options:
    preserve_layout: false          # Disable for performance
    extract_tables: false          # Disable for performance
    extract_images: false          # Disable for performance
    ocr_confidence_threshold: 0.8  # High threshold for speed

metrics:
  enabled: true
  collection_interval: 60.0        # Less frequent to reduce overhead
  retention_hours: 24              # Shorter retention
  storage_backend: "file"
  compression_enabled: true         # Enable compression
  compression_threshold: 100       # Compress early
```

### Dynamic Configuration Adjustment

#### Runtime Configuration Updates

```python
# Dynamic configuration adjustment for performance optimization
class DynamicConfigManager:
    def __init__(self, config: Config):
        self.config = config
        self.original_config = config.to_dict()
        self.performance_monitor = PerformanceMonitor()
        self.adjustment_history = []
    
    async def start_auto_tuning(self):
        """Start automatic performance tuning."""
        while True:
            try:
                # Get current performance metrics
                metrics = await self.performance_monitor.get_current_metrics()
                
                # Analyze performance and adjust configuration
                adjustments = self.analyze_performance(metrics)
                
                # Apply adjustments
                for adjustment in adjustments:
                    await self.apply_adjustment(adjustment)
                
                # Wait before next tuning cycle
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                logger.error(f"Auto-tuning error: {e}")
                await asyncio.sleep(60)  # Back off on error
    
    def analyze_performance(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze performance metrics and recommend adjustments."""
        adjustments = []
        
        # CPU usage analysis
        cpu_usage = metrics.get('cpu_usage_percent', 0)
        if cpu_usage > 85:
            adjustments.append({
                'parameter': 'performance.max_connections',
                'action': 'decrease',
                'value': max(10, self.config.performance.max_connections - 20),
                'reason': 'High CPU usage detected'
            })
        elif cpu_usage < 50:
            adjustments.append({
                'parameter': 'performance.max_connections',
                'action': 'increase',
                'value': min(1000, self.config.performance.max_connections + 20),
                'reason': 'Low CPU usage, can handle more connections'
            })
        
        # Memory usage analysis
        memory_usage = metrics.get('memory_usage_percent', 0)
        if memory_usage > 85:
            adjustments.append({
                'parameter': 'docling.max_file_size',
                'action': 'decrease',
                'value': max(10485760, self.config.docling.max_file_size - 10485760),
                'reason': 'High memory usage detected'
            })
        
        # Response time analysis
        response_time_p95 = metrics.get('response_time_p95', 0)
        if response_time_p95 > 2000:  # 2 seconds
            adjustments.append({
                'parameter': 'performance.tool_timeout',
                'action': 'decrease',
                'value': max(10.0, self.config.performance.tool_timeout - 5.0),
                'reason': 'High response times detected'
            })
        
        return adjustments
    
    async def apply_adjustment(self, adjustment: Dict[str, Any]):
        """Apply configuration adjustment."""
        try:
            parameter = adjustment['parameter']
            action = adjustment['action']
            value = adjustment['value']
            reason = adjustment['reason']
            
            # Apply adjustment based on parameter
            if parameter == 'performance.max_connections':
                self.config.performance.max_connections = value
            elif parameter == 'docling.max_file_size':
                self.config.docling.max_file_size = value
            elif parameter == 'performance.tool_timeout':
                self.config.performance.tool_timeout = value
            
            # Record adjustment
            adjustment_record = {
                'timestamp': time.time(),
                'parameter': parameter,
                'action': action,
                'old_value': self.get_original_value(parameter),
                'new_value': value,
                'reason': reason
            }
            self.adjustment_history.append(adjustment_record)
            
            logger.info(f"Applied configuration adjustment: {adjustment_record}")
            
        except Exception as e:
            logger.error(f"Failed to apply adjustment {adjustment}: {e}")
    
    def get_original_value(self, parameter: str) -> Any:
        """Get original configuration value."""
        keys = parameter.split('.')
        value = self.original_config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
    
    def rollback_adjustments(self):
        """Rollback all adjustments to original configuration."""
        logger.info("Rolling back configuration adjustments")
        
        # Restore original configuration
        for key, value in self.original_config.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        # Clear adjustment history
        self.adjustment_history.clear()
        
        logger.info("Configuration rollback completed")
```

#### Performance-Based Configuration Profiles

```python
# Performance-based configuration profiles
class PerformanceProfileManager:
    def __init__(self):
        self.profiles = {
            'low_latency': {
                'performance': {
                    'tool_timeout': 10.0,
                    'max_connections': 500,
                    'batch_processing': {
                        'enabled': False,
                        'batch_size': 5,
                        'batch_timeout': 1.0
                    }
                },
                'sse': {
                    'keepalive_interval': 0.01,
                    'batch_events': False,
                    'compression_threshold': 256
                }
            },
            'high_throughput': {
                'performance': {
                    'tool_timeout': 30.0,
                    'max_connections': 1000,
                    'batch_processing': {
                        'enabled': True,
                        'batch_size': 50,
                        'batch_timeout': 5.0
                    }
                },
                'sse': {
                    'keepalive_interval': 0.1,
                    'batch_events': True,
                    'batch_size': 50,
                    'compression_threshold': 1024
                }
            },
            'resource_efficient': {
                'performance': {
                    'tool_timeout': 15.0,
                    'max_connections': 50,
                    'batch_processing': {
                        'enabled': True,
                        'batch_size': 5,
                        'batch_timeout': 2.0
                    }
                },
                'docling': {
                    'max_file_size': 10485760,  # 10MB
                    'enable_cache': False
                }
            }
        }
    
    def apply_profile(self, config: Config, profile_name: str) -> Config:
        """Apply performance profile to configuration."""
        if profile_name not in self.profiles:
            raise ValueError(f"Unknown profile: {profile_name}")
        
        profile = self.profiles[profile_name]
        
        # Apply profile settings to configuration
        for section, settings in profile.items():
            if hasattr(config, section):
                section_obj = getattr(config, section)
                for key, value in settings.items():
                    if hasattr(section_obj, key):
                        setattr(section_obj, key, value)
                    elif isinstance(value, dict):
                        # Handle nested dictionaries
                        nested_obj = getattr(section_obj, key)
                        for nested_key, nested_value in value.items():
                            if hasattr(nested_obj, nested_key):
                                setattr(nested_obj, nested_key, nested_value)
        
        logger.info(f"Applied performance profile: {profile_name}")
        return config
    
    def get_recommended_profile(self, metrics: Dict[str, Any]) -> str:
        """Get recommended profile based on current metrics."""
        cpu_usage = metrics.get('cpu_usage_percent', 0)
        memory_usage = metrics.get('memory_usage_percent', 0)
        response_time = metrics.get('response_time_p95', 0)
        connection_count = metrics.get('active_connections', 0)
        
        # Decision logic for profile recommendation
        if response_time > 1000:  # High latency
            return 'low_latency'
        elif connection_count > 500:  # High connection count
            return 'high_throughput'
        elif memory_usage > 80 or cpu_usage > 80:  # Resource constrained
            return 'resource_efficient'
        else:
            return 'high_throughput'  # Default profile
```

## Tools and Utilities

Various tools and utilities are available for performance monitoring, profiling, and optimization of the Docling MCP Server.

### Performance Profiling Tools

#### Built-in Profiling

```python
# Built-in profiling utilities
class PerformanceProfiler:
    def __init__(self):
        self.profilers = {
            'cpu': CPUProfiler(),
            'memory': MemoryProfiler(),
            'network': NetworkProfiler()
        }
    
    async def start_profiling(self, profiler_types: List[str] = None):
        """Start specified profilers."""
        if profiler_types is None:
            profiler_types = ['cpu', 'memory', 'network']
        
        for profiler_type in profiler_types:
            if profiler_type in self.profilers:
                profiler = self.profilers[profiler_type]
                if hasattr(profiler, 'start_profiling'):
                    profiler.start_profiling()
                elif hasattr(profiler, 'start'):
                    profiler.start()
                
                logger.info(f"Started {profiler_type} profiling")
    
    async def stop_profiling(self, profiler_types: List[str] = None):
        """Stop specified profilers."""
        if profiler_types is None:
            profiler_types = list(self.profilers.keys())
        
        for profiler_type in profiler_types:
            if profiler_type in self.profilers:
                profiler = self.profilers[profiler_type]
                if hasattr(profiler, 'stop_profiling'):
                    profiler.stop_profiling()
                elif hasattr(profiler, 'stop'):
                    profiler.stop()
                
                logger.info(f"Stopped {profiler_type} profiling")
    
    def get_profiling_results(self, profiler_type: str) -> Dict[str, Any]:
        """Get results from specified profiler."""
        if profiler_type not in self.profilers:
            return {}
        
        profiler = self.profilers[profiler_type]
        
        if hasattr(profiler, 'get_results'):
            return profiler.get_results()
        elif hasattr(profiler, 'get_summary'):
            return profiler.get_summary()
        else:
            return {}
```

#### External Profiling Tools

1. **Py-Spy**: Sampling profiler for Python applications
2. **Memory Profiler**: Line-by-line memory usage analysis
3. **Line Profiler**: Line-by-line execution time analysis
4. **AIOHTTP Debug Toolbar**: Debug toolbar for aiohttp applications

```bash
# Install profiling tools
pip install py-spy memory-profiler line-profiler aiohttp-debugtoolbar

# Py-Spy usage examples
py-spy top --pid <process_id>                    # Real-time profiling
py-spy record -o profile.svg --pid <process_id>  # Record flame graph
py-spy dump --pid <process_id>                   # Dump stack traces

# Memory profiler usage
python -m memory_profiler docling_mcp_server.py

# Line profiler usage
kernprof -l -v docling_mcp_server.py
```

### Load Testing Tools

#### Custom Load Testing Framework

```python
# Custom load testing framework
class LoadTestingFramework:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.scenarios = {}
        self.results = {}
    
    def register_scenario(self, name: str, scenario: Dict[str, Any]):
        """Register a load testing scenario."""
        self.scenarios[name] = scenario
    
    async def run_scenario(self, name: str, duration: int = 60) -> Dict[str, Any]:
        """Run a specific load testing scenario."""
        if name not in self.scenarios:
            raise ValueError(f"Unknown scenario: {name}")
        
        scenario = self.scenarios[name]
        
        # Create load tester
        load_tester = LoadTester(
            self.base_url,
            max_concurrent=scenario.get('concurrent_users', 100)
        )
        
        # Run the test
        result = await load_tester.run_load_test(
            concurrent_users=scenario['concurrent_users'],
            duration=duration
        )
        
        self.results[name] = result
        return result
    
    def compare_scenarios(self, scenario_names: List[str]) -> Dict[str, Any]:
        """Compare results of multiple scenarios."""
        comparison = {
            'scenarios': {},
            'recommendations': []
        }
        
        for name in scenario_names:
            if name in self.results:
                comparison['scenarios'][name] = self.results[name]
        
        # Generate recommendations
        best_throughput = max(
            (r['requests_per_second'] for r in comparison['scenarios'].values()),
            default=0
        )
        
        for name, result in comparison['scenarios'].items():
            if result['requests_per_second'] == best_throughput:
                comparison['recommendations'].append(
                    f"Scenario '{name}' has the best throughput: {best_throughput:.2f} req/s"
                )
        
        return comparison
```

#### External Load Testing Tools

1. **Apache Bench (ab)**: Simple HTTP load testing
2. **JMeter**: Comprehensive load testing tool
3. **Locust**: Python-based load testing framework
4. **K6**: Modern load testing tool

```bash
# Apache Bench example
ab -n 1000 -c 10 http://localhost:3020/health

# Locust example (locustfile.py)
from locust import HttpUser, task, between

class DoclingMCPUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def health_check(self):
        self.client.get("/health")
    
    @task
    def convert_document(self):
        self.client.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": "test",
            "method": "tools/call",
            "params": {
                "name": "convert_document",
                "arguments": {
                    "file_path": "/test/document.pdf",
                    "output_format": "markdown"
                }
            }
        })

# Run Locust
locust -f locustfile.py --host=http://localhost:3020
```

### Monitoring and Analysis Tools

#### Real-time Monitoring Dashboard

```python
# Real-time monitoring dashboard
class MonitoringDashboard:
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.alert_manager = AlertManager()
        self.dashboard_data = {}
    
    async def start_dashboard(self, port: int = 8080):
        """Start monitoring dashboard."""
        app = web.Application()
        
        # Add routes
        app.router.add_get('/', self.dashboard_handler)
        app.router.add_get('/api/metrics', self.metrics_api_handler)
        app.router.add_get('/api/alerts', self.alerts_api_handler)
        app.router.add_get('/ws', self.websocket_handler)
        
        # Start server
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        
        logger.info(f"Monitoring dashboard started on port {port}")
    
    async def dashboard_handler(self, request: Request) -> Response:
        """Serve dashboard HTML."""
        html = self.get_dashboard_html()
        return web.Response(text=html, content_type='text/html')
    
    async def metrics_api_handler(self, request: Request) -> Response:
        """Serve metrics API."""
        metrics = self.metrics_collector.get_current_metrics()
        return web.json_response(metrics)
    
    async def alerts_api_handler(self, request: Request) -> Response:
        """Serve alerts API."""
        alerts = self.alert_manager.get_active_alerts()
        return web.json_response(alerts)
    
    async def websocket_handler(self, request: Request) -> web.WebSocketResponse:
        """Handle WebSocket connections for real-time updates."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        try:
            while True:
                # Get current metrics
                metrics = self.metrics_collector.get_current_metrics()
                
                # Send metrics to client
                await ws.send_str(json.dumps(metrics))
                
                # Wait before next update
                await asyncio.sleep(1)
                
        except ConnectionResetError:
            pass
        finally:
            await ws.close()
        
        return ws
    
    def get_dashboard_html(self) -> str:
        """Generate dashboard HTML."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Docling MCP Monitoring Dashboard</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .metric-card { border: 1px solid #ddd; padding: 15px; margin: 10px; }
                .chart-container { width: 45%; display: inline-block; margin: 10px; }
            </style>
        </head>
        <body>
            <h1>Docling MCP Monitoring Dashboard</h1>
            
            <div class="metric-card">
                <h2>System Metrics</h2>
                <div id="system-metrics"></div>
            </div>
            
            <div class="chart-container">
                <canvas id="cpu-chart"></canvas>
            </div>
            
            <div class="chart-container">
                <canvas id="memory-chart"></canvas>
            </div>
            
            <div class="chart-container">
                <canvas id="requests-chart"></canvas>
            </div>
            
            <div class="chart-container">
                <canvas id="response-time-chart"></canvas>
            </div>
            
            <script>
                // WebSocket connection for real-time updates
                const ws = new WebSocket('ws://localhost:8080/ws');
                
                // Chart configurations
                const cpuChart = new Chart(document.getElementById('cpu-chart'), {
                    type: 'line',
                    data: { labels: [], datasets: [{ label: 'CPU %', data: [] }] },
                    options: { responsive: true, scales: { y: { beginAtZero: true, max: 100 } } }
                });
                
                const memoryChart = new Chart(document.getElementById('memory-chart'), {
                    type: 'line',
                    data: { labels: [], datasets: [{ label: 'Memory %', data: [] }] },
                    options: { responsive: true, scales: { y: { beginAtZero: true, max: 100 } } }
                });
                
                // WebSocket message handler
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    updateCharts(data);
                };
                
                function updateCharts(data) {
                    const timestamp = new Date().toLocaleTimeString();
                    
                    // Update CPU chart
                    cpuChart.data.labels.push(timestamp);
                    cpuChart.data.datasets[0].data.push(data.resource_metrics.cpu_usage_percent);
                    cpuChart.data.labels.shift();
                    cpuChart.data.datasets[0].data.shift();
                    cpuChart.update();
                    
                    // Update memory chart
                    memoryChart.data.labels.push(timestamp);
                    memoryChart.data.datasets[0].data.push(data.resource_metrics.memory_usage_percent);
                    memoryChart.data.labels.shift();
                    memoryChart.data.datasets[0].data.shift();
                    memoryChart.update();
                }
            </script>
        </body>
        </html>
        """
```

#### Log Analysis Tools

```python
# Log analysis utilities
class LogAnalyzer:
    def __init__(self, log_file: str):
        self.log_file = log_file
        self.patterns = {
            'error': r'ERROR',
            'warning': r'WARNING',
            'request': r'Request completed',
            'connection': r'SSE connection',
            'timeout': r'timed out'
        }
    
    def analyze_logs(self, start_time: str = None, end_time: str = None) -> Dict[str, Any]:
        """Analyze log file for performance insights."""
        analysis = {
            'total_lines': 0,
            'error_count': 0,
            'warning_count': 0,
            'request_count': 0,
            'connection_count': 0,
            'timeout_count': 0,
            'error_patterns': {},
            'performance_issues': [],
            'recommendations': []
        }
        
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    analysis['total_lines'] += 1
                    
                    # Check for different patterns
                    for pattern_name, pattern in self.patterns.items():
                        if re.search(pattern, line):
                            analysis[f'{pattern_name}_count'] += 1
                            
                            # Extract additional information
                            if pattern_name == 'error':
                                self.analyze_error_line(line, analysis)
                            elif pattern_name == 'request':
                                self.analyze_request_line(line, analysis)
                            elif pattern_name == 'timeout':
                                self.analyze_timeout_line(line, analysis)
        
        except FileNotFoundError:
            logger.error(f"Log file not found: {self.log_file}")
            return analysis
        
        # Generate recommendations
        analysis['recommendations'] = self.generate_recommendations(analysis)
        
        return analysis
    
    def analyze_error_line(self, line: str, analysis: Dict[str, Any]):
        """Analyze error line for patterns."""
        # Extract error type
        error_match = re.search(r'ERROR.*?:\s*(.+)', line)
        if error_match:
            error_type = error_match.group(1).strip()
            analysis['error_patterns'][error_type] = analysis['error_patterns'].get(error_type, 0) + 1
    
    def analyze_request_line(self, line: str, analysis: Dict[str, Any]):
        """Analyze request line for performance."""
        # Extract response time
        time_match = re.search(r'(\d+\.?\d*)ms', line)
        if time_match:
            response_time = float(time_match.group(1))
            if response_time > 5000:  # 5 seconds
                analysis['performance_issues'].append({
                    'type': 'slow_request',
                    'response_time': response_time,
                    'line': line.strip()
                })
    
    def analyze_timeout_line(self, line: str, analysis: Dict[str, Any]):
        """Analyze timeout line for patterns."""
        # Extract timeout type
        timeout_match = re.search(r'timed out.*?:\s*(.+)', line)
        if timeout_match:
            timeout_type = timeout_match.group(1).strip()
            analysis['performance_issues'].append({
                'type': 'timeout',
                'timeout_type': timeout_type,
                'line': line.strip()
            })
    
    def generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on log analysis."""
        recommendations = []
        
        # Error rate recommendations
        if analysis['error_count'] > 0:
            error_rate = (analysis['error_count'] / analysis['total_lines']) * 100
            if error_rate > 5:
                recommendations.append(
                    f"High error rate ({error_rate:.1f}%). "
                    "Review error patterns and fix underlying issues."
                )
        
        # Timeout recommendations
        if analysis['timeout_count'] > 0:
            recommendations.append(
                f"Found {analysis['timeout_count']} timeouts. "
                "Consider increasing timeout values or optimizing performance."
            )
        
        # Performance issue recommendations
        slow_requests = [i for i in analysis['performance_issues'] if i['type'] == 'slow_request']
        if len(slow_requests) > 5:
            recommendations.append(
                f"Found {len(slow_requests)} slow requests (>5s). "
                "Investigate performance bottlenecks."
            )
        
        return recommendations
```

### Optimization Recommendation Engine

#### AI-Based Performance Recommendations

```python
# Performance optimization recommendation engine
class OptimizationEngine:
    def __init__(self):
        self.rules = self.load_optimization_rules()
        self.ml_model = None  # Could be trained on historical data
    
    def load_optimization_rules(self) -> List[Dict[str, Any]]:
        """Load optimization rules."""
        return [
            {
                'name': 'high_cpu_usage',
                'condition': lambda metrics: metrics.get('cpu_usage_percent', 0) > 80,
                'recommendation': 'Reduce max_connections or optimize CPU-intensive operations',
                'config_changes': {
                    'performance.max_connections': 'decrease',
                    'performance.tool_timeout': 'decrease'
                }
            },
            {
                'name': 'high_memory_usage',
                'condition': lambda metrics: metrics.get('memory_usage_percent', 0) > 85,
                'recommendation': 'Reduce max_file_size or enable memory optimization',
                'config_changes': {
                    'docling.max_file_size': 'decrease',
                    'docling.enable_cache': 'false'
                }
            },
            {
                'name': 'high_response_time',
                'condition': lambda metrics: metrics.get('response_time_p95', 0) > 2000,
                'recommendation': 'Enable batch processing or optimize document processing',
                'config_changes': {
                    'performance.batch_processing.enabled': 'true',
                    'performance.batch_processing.batch_size': 'increase'
                }
            },
            {
                'name': 'high_error_rate',
                'condition': lambda metrics: metrics.get('error_rate', 0) > 5,
                'recommendation': 'Reduce load or fix underlying issues',
                'config_changes': {
                    'performance.max_connections': 'decrease',
                    'performance.rate_limit_requests': 'decrease'
                }
            }
        ]
    
    def analyze_and_recommend(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze metrics and provide recommendations."""
        recommendations = []
        triggered_rules = []
        
        for rule in self.rules:
            if rule['condition'](metrics):
                recommendations.append(rule['recommendation'])
                triggered_rules.append(rule['name'])
        
        # Calculate optimization score
        optimization_score = self.calculate_optimization_score(metrics)
        
        return {
            'timestamp': time.time(),
            'metrics': metrics,
            'optimization_score': optimization_score,
            'recommendations': recommendations,
            'triggered_rules': triggered_rules,
            'config_changes': self.get_config_changes(triggered_rules)
        }
    
    def calculate_optimization_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate optimization score (0-100, higher is better)."""
        score = 100.0
        
        # CPU usage impact
        cpu_usage = metrics.get('cpu_usage_percent', 0)
        if cpu_usage > 80:
            score -= (cpu_usage - 80) * 2
        elif cpu_usage < 30:
            score -= (30 - cpu_usage) * 0.5  # Underutilization
        
        # Memory usage impact
        memory_usage = metrics.get('memory_usage_percent', 0)
        if memory_usage > 85:
            score -= (memory_usage - 85) * 3
        elif memory_usage < 30:
            score -= (30 - memory_usage) * 0.5
        
        # Response time impact
        response_time_p95 = metrics.get('response_time_p95', 0)
        if response_time_p95 > 2000:
            score -= (response_time_p95 - 2000) / 100
        elif response_time_p95 < 100:
            score += 5  # Bonus for fast response
        
        # Error rate impact
        error_rate = metrics.get('error_rate', 0)
        if error_rate > 5:
            score -= error_rate * 5
        
        return max(0, min(100, score))
    
    def get_config_changes(self, triggered_rules: List[str]) -> Dict[str, str]:
        """Get configuration changes for triggered rules."""
        config_changes = {}
        
        for rule in self.rules:
            if rule['name'] in triggered_rules:
                config_changes.update(rule['config_changes'])
        
        return config_changes
    
    def train_ml_model(self, historical_data: List[Dict[str, Any]]):
        """Train ML model on historical performance data."""
        # This would implement machine learning for better recommendations
        # For now, it's a placeholder
        pass
    
    def predict_performance(self, config_changes: Dict[str, Any], 
                          current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Predict performance impact of configuration changes."""
        # Simple prediction based on rules
        predicted_metrics = current_metrics.copy()
        
        for param, change in config_changes.items():
            if param == 'performance.max_connections':
                if change == 'decrease':
                    predicted_metrics['cpu_usage_percent'] *= 0.9
                    predicted_metrics['memory_usage_percent'] *= 0.95
                elif change == 'increase':
                    predicted_metrics['cpu_usage_percent'] *= 1.1
                    predicted_metrics['memory_usage_percent'] *= 1.05
            
            elif param == 'docling.max_file_size':
                if change == 'decrease':
                    predicted_metrics['memory_usage_percent'] *= 0.9
                    predicted_metrics['response_time_p95'] *= 0.95
        
        return predicted_metrics
```

## Troubleshooting Performance Issues

This section provides systematic approaches to identifying and resolving common performance issues in the Docling MCP Server.

### Performance Issue Diagnosis

#### Systematic Diagnostic Approach

```python
# Performance diagnostic system
class PerformanceDiagnostics:
    def __init__(self):
        self.diagnostic_steps = [
            self.check_system_resources,
            self.check_configuration,
            self.check_network_connectivity,
            self.check_disk_performance,
            self.check_memory_usage,
            self.check_cpu_usage,
            self.check_application_logs,
            self.check_metrics_data
        ]
    
    async def run_full_diagnosis(self) -> Dict[str, Any]:
        """Run comprehensive performance diagnosis."""
        diagnosis = {
            'timestamp': time.time(),
            'overall_health': 'unknown',
            'issues': [],
            'recommendations': [],
            'detailed_results': {}
        }
        
        for step in self.diagnostic_steps:
            try:
                result = await step()
                diagnosis['detailed_results'][step.__name__] = result
                
                # Analyze result for issues
                issues = self.analyze_step_result(step.__name__, result)
                diagnosis['issues'].extend(issues)
                
            except Exception as e:
                diagnosis['issues'].append({
                    'step': step.__name__,
                    'type': 'diagnostic_error',
                    'message': f"Diagnostic step failed: {e}"
                })
        
        # Determine overall health
        if not diagnosis['issues']:
            diagnosis['overall_health'] = 'healthy'
        elif len(diagnosis['issues']) < 3:
            diagnosis['overall_health'] = 'warning'
        else:
            diagnosis['overall_health'] = 'critical'
        
        # Generate recommendations
        diagnosis['recommendations'] = self.generate_recommendations(diagnosis['issues'])
        
        return diagnosis
    
    async def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource availability."""
        import psutil
        
        return {
            'cpu_count': psutil.cpu_count(),
            'cpu_usage_percent': psutil.cpu_percent(interval=1),
            'memory_total': psutil.virtual_memory().total,
            'memory_available': psutil.virtual_memory().available,
            'memory_usage_percent': psutil.virtual_memory().percent,
            'disk_total': psutil.disk_usage('/').total,
            'disk_free': psutil.disk_usage('/').free,
            'disk_usage_percent': psutil.disk_usage('/').percent,
            'boot_time': psutil.boot_time()
        }
    
    async def check_configuration(self) -> Dict[str, Any]:
        """Check configuration for performance issues."""
        # This would check current configuration
        # For now, return placeholder
        return {
            'config_loaded': True,
            'config_valid': True,
            'performance_settings': {
                'max_connections': 'configured',
                'tool_timeout': 'configured',
                'batch_processing': 'configured'
            }
        }
    
    async def check_network_connectivity(self) -> Dict[str, Any]:
        """Check network connectivity and performance."""
        import socket
        import time
        
        results = {}
        
        # Test localhost connectivity
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('localhost', 3020))
            sock.close()
            
            results['localhost_connectivity'] = result == 0
            results['localhost_latency'] = (time.time() - start_time) * 1000
        except Exception as e:
            results['localhost_connectivity'] = False
            results['localhost_error'] = str(e)
        
        return results
    
    async def check_disk_performance(self) -> Dict[str, Any]:
        """Check disk I/O performance."""
        import tempfile
        import os
        
        results = {}
        
        try:
            # Test write performance
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                start_time = time.time()
                data = b'x' * 1024 * 1024  # 1MB of data
                for _ in range(10):  # Write 10MB
                    tmp.write(data)
                tmp.flush()
                os.fsync(tmp.fileno())
                write_time = time.time() - start_time
                tmp_path = tmp.name
            
            # Test read performance
            start_time = time.time()
            with open(tmp_path, 'rb') as f:
                while f.read(1024 * 1024):  # Read 1MB chunks
                    pass
            read_time = time.time() - start_time
            
            # Cleanup
            os.unlink(tmp_path)
            
            results['write_speed_mbps'] = 10 / write_time  # MB/s
            results['read_speed_mbps'] = 10 / read_time   # MB/s
            results['disk_performance_good'] = (
                results['write_speed_mbps'] > 50 and 
                results['read_speed_mbps'] > 100
            )
            
        except Exception as e:
            results['error'] = str(e)
            results['disk_performance_good'] = False
        
        return results
    
    def analyze_step_result(self, step_name: str, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze diagnostic step result for issues."""
        issues = []
        
        if step_name == 'check_system_resources':
            if result.get('cpu_usage_percent', 0) > 90:
                issues.append({
                    'step': step_name,
                    'type': 'high_cpu_usage',
                    'severity': 'critical',
                    'message': f"High CPU usage: {result['cpu_usage_percent']}%"
                })
            
            if result.get('memory_usage_percent', 0) > 90:
                issues.append({
                    'step': step_name,
                    'type': 'high_memory_usage',
                    'severity': 'critical',
                    'message': f"High memory usage: {result['memory_usage_percent']}%"
                })
            
            if result.get('disk_usage_percent', 0) > 95:
                issues.append({
                    'step': step_name,
                    'type': 'low_disk_space',
                    'severity': 'critical',
                    'message': f"Low disk space: {result['disk_usage_percent']}% used"
                })
        
        elif step_name == 'check_network_connectivity':
            if not result.get('localhost_connectivity', False):
                issues.append({
                    'step': step_name,
                    'type': 'connectivity_issue',
                    'severity': 'critical',
                    'message': "Cannot connect to localhost:3020"
                })
            
            latency = result.get('localhost_latency', 0)
            if latency > 100:  # 100ms threshold
                issues.append({
                    'step': step_name,
                    'type': 'high_latency',
                    'severity': 'warning',
                    'message': f"High localhost latency: {latency:.2f}ms"
                })
        
        elif step_name == 'check_disk_performance':
            if not result.get('disk_performance_good', False):
                issues.append({
                    'step': step_name,
                    'type': 'poor_disk_performance',
                    'severity': 'warning',
                    'message': "Disk performance below optimal thresholds"
                })
        
        return issues
    
    def generate_recommendations(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on identified issues."""
        recommendations = []
        
        for issue in issues:
            if issue['type'] == 'high_cpu_usage':
                recommendations.append(
                    "Reduce max_connections or optimize CPU-intensive operations. "
                    "Consider scaling horizontally."
                )
            elif issue['type'] == 'high_memory_usage':
                recommendations.append(
                    "Reduce max_file_size or enable memory optimization. "
                    "Check for memory leaks."
                )
            elif issue['type'] == 'low_disk_space':
                recommendations.append(
                    "Free up disk space or move to larger storage. "
                    "Consider implementing log rotation."
                )
            elif issue['type'] == 'connectivity_issue':
                recommendations.append(
                    "Check if the service is running and listening on port 3020. "
                    "Verify firewall settings."
                )
            elif issue['type'] == 'high_latency':
                recommendations.append(
                    "Check for network congestion or system overload. "
                    "Optimize network configuration."
                )
            elif issue['type'] == 'poor_disk_performance':
                recommendations.append(
                    "Consider using faster storage (SSD) or optimize disk I/O patterns. "
                    "Check for disk fragmentation."
                )
        
        return list(set(recommendations))  # Remove duplicates
```

### Common Performance Issues and Solutions

#### High CPU Usage

**Symptoms:**
- CPU usage consistently above 80%
- Slow response times
- System becoming unresponsive

**Causes:**
- Too many concurrent connections
- Inefficient document processing
- CPU-intensive OCR operations
- Lack of connection pooling

**Solutions:**

1. **Reduce Concurrent Connections**
```yaml
performance:
  max_connections: 50  # Reduce from default
  tool_timeout: 15.0   # Shorter timeout
```

2. **Optimize Document Processing**
```yaml
docling:
  pipeline_options:
    ocr_engine: "tesseract"  # Use faster OCR
    ocr_languages: ["eng"]   # Single language
    preserve_layout: false  # Disable layout preservation
```

3. **Enable Connection Pooling**
```python
# Implement connection pooling
connector = aiohttp.TCPConnector(
    limit=50,              # Reduce pool size
    limit_per_host=20,
    keepalive_timeout=30
)
```

#### High Memory Usage

**Symptoms:**
- Memory usage consistently above 85%
- Out-of-memory errors
- System swapping

**Causes:**
- Large document processing
- Memory leaks
- Inefficient caching
- Too much data in memory

**Solutions:**

1. **Reduce File Size Limits**
```yaml
docling:
  max_file_size: 10485760  # 10MB limit
  enable_cache: false       # Disable cache if memory constrained
```

2. **Implement Memory Management**
```python
# Add memory monitoring and cleanup
async def memory_monitor():
    process = psutil.Process()
    while True:
        memory_percent = process.memory_percent()
        if memory_percent > 80:
            gc.collect()  # Force garbage collection
            clear_caches()
        await asyncio.sleep(60)
```

3. **Use Streaming Processing**
```python
# Process documents in streams
async def process_document_stream(file_path: str):
    async with aiofiles.open(file_path, 'rb') as file:
        while True:
            chunk = await file.read(8192)
            if not chunk:
                break
            # Process chunk
            await process_chunk(chunk)
```

#### Slow Response Times

**Symptoms:**
- P95 response time > 2 seconds
- User complaints about slowness
- Timeouts occurring

**Causes:**
- Network latency
- Disk I/O bottlenecks
- Inefficient algorithms
- Database queries

**Solutions:**

1. **Enable Batch Processing**
```yaml
performance:
  batch_processing:
    enabled: true
    batch_size: 20
    batch_timeout: 2.0
```

2. **Optimize Network Settings**
```yaml
sse:
  keepalive_interval: 0.05   # Faster keepalive
  batch_events: true         # Enable batching
  compression_threshold: 512 # Lower threshold
```

3. **Use Caching**
```python
# Implement multi-level caching
@lru_cache(maxsize=100)
def get_cached_result(file_hash: str):
    # Check cache first
    pass
```

#### Connection Issues

**Symptoms:**
- Connection refused errors
- High connection timeout rate
- SSE stream disconnections

**Causes:**
- Port conflicts
- Firewall blocking
- Resource exhaustion
- Configuration errors

**Solutions:**

1. **Check Port Availability**
```bash
# Check if port is in use
netstat -tlnp | grep 3020
lsof -i :3020
```

2. **Adjust Connection Settings**
```yaml
performance:
  max_connections: 100        # Adjust based on resources
  connection_pool:
    max_size: 50
    idle_timeout: 300
```

3. **Implement Connection Health Checks**
```python
# Add connection health monitoring
async def health_check():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:3020/health') as response:
                return response.status == 200
    except:
        return False
```

### Performance Recovery Procedures

#### Emergency Recovery

```python
# Emergency recovery procedures
class EmergencyRecovery:
    def __init__(self, config: Config):
        self.config = config
        self.recovery_actions = [
            self.clear_caches,
            self.reduce_connections,
            self.restart_services,
            self.restore_defaults
        ]
    
    async def emergency_recovery(self) -> Dict[str, Any]:
        """Perform emergency recovery procedures."""
        recovery_log = {
            'timestamp': time.time(),
            'actions_taken': [],
            'success': False,
            'final_state': 'unknown'
        }
        
        for action in self.recovery_actions:
            try:
                result = await action()
                recovery_log['actions_taken'].append({
                    'action': action.__name__,
                    'result': result
                })
                
                if result.get('success', False):
                    recovery_log['success'] = True
                    recovery_log['final_state'] = 'recovered'
                    break
                    
            except Exception as e:
                recovery_log['actions_taken'].append({
                    'action': action.__name__,
                    'error': str(e)
                })
        
        return recovery_log
    
    async def clear_caches(self) -> Dict[str, Any]:
        """Clear all caches to free memory."""
        try:
            # Clear document cache
            if hasattr(self, 'document_cache'):
                self.document_cache.clear()
            
            # Clear metrics cache
            if hasattr(self, 'metrics_collector'):
                self.metrics_collector.reset_metrics()
            
            # Force garbage collection
            import gc
            gc.collect()
            
            return {'success': True, 'message': 'Caches cleared successfully'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def reduce_connections(self) -> Dict[str, Any]:
        """Reduce maximum connections to alleviate load."""
        try:
            original_max = self.config.performance.max_connections
            self.config.performance.max_connections = max(10, original_max // 2)
            
            return {
                'success': True,
                'message': f"Reduced max connections from {original_max} to {self.config.performance.max_connections}"
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def restart_services(self) -> Dict[str, Any]:
        """Restart critical services."""
        try:
            # This would implement service restart logic
            # For now, return placeholder
            return {'success': True, 'message': 'Services restarted'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def restore_defaults(self) -> Dict[str, Any]:
        """Restore default configuration."""
        try:
            # Load default configuration
            from config import load_config
            default_config = load_config(environment='default')
            
            # Apply critical defaults
            self.config.performance.max_connections = default_config.performance.max_connections
            self.config.performance.tool_timeout = default_config.performance.tool_timeout
            self.config.docling.max_file_size = default_config.docling.max_file_size
            
            return {'success': True, 'message': 'Default configuration restored'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
```

#### Gradual Performance Recovery

```python
# Gradual performance recovery
class GradualRecovery:
    def __init__(self, config: Config):
        self.config = config
        self.recovery_steps = [
            {'name': 'reduce_connections', 'factor': 0.8},
            {'name': 'increase_timeout', 'factor': 1.2},
            {'name': 'enable_batching', 'factor': None},
            {'name': 'reduce_file_size', 'factor': 0.7}
        ]
    
    async def gradual_recovery(self) -> Dict[str, Any]:
        """Perform gradual recovery with monitoring."""
        recovery_log = {
            'timestamp': time.time(),
            'steps_completed': [],
            'final_state': 'unknown'
        }
        
        for step in self.recovery_steps:
            try:
                # Apply recovery step
                result = await self.apply_recovery_step(step)
                recovery_log['steps_completed'].append({
                    'step': step['name'],
                    'result': result
                })
                
                # Monitor for improvement
                await asyncio.sleep(30)  # Wait for changes to take effect
                
                if await self.check_improvement():
                    recovery_log['final_state'] = 'improved'
                    break
                    
            except Exception as e:
                recovery_log['steps_completed'].append({
                    'step': step['name'],
                    'error': str(e)
                })
        
        return recovery_log
    
    async def apply_recovery_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a single recovery step."""
        name = step['name']
        factor = step['factor']
        
        if name == 'reduce_connections':
            original = self.config.performance.max_connections
            self.config.performance.max_connections = int(original * factor)
            return {
                'success': True,
                'message': f"Reduced connections from {original} to {self.config.performance.max_connections}"
            }
        
        elif name == 'increase_timeout':
            original = self.config.performance.tool_timeout
            self.config.performance.tool_timeout = original * factor
            return {
                'success': True,
                'message': f"Increased timeout from {original} to {self.config.performance.tool_timeout}"
            }
        
        elif name == 'enable_batching':
            self.config.performance.batch_processing.enabled = True
            return {
                'success': True,
                'message': "Enabled batch processing"
            }
        
        elif name == 'reduce_file_size':
            original = self.config.docling.max_file_size
            self.config.docling.max_file_size = int(original * factor)
            return {
                'success': True,
                'message': f"Reduced max file size from {original} to {self.config.docling.max_file_size}"
            }
        
        return {'success': False, 'message': f'Unknown step: {name}'}
    
    async def check_improvement(self) -> bool:
        """Check if performance has improved."""
        # This would implement performance checking logic
        # For now, return placeholder
        return False
```

This comprehensive performance tuning guide provides detailed strategies for optimizing the Docling MCP Server across various deployment scenarios. The guide covers all aspects of performance optimization from low-level resource management to high-level architectural considerations, with practical examples and configuration recommendations for different use cases.