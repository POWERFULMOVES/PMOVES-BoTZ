# Docling MCP Node.js Client Examples

This directory contains comprehensive Node.js client examples for the Docling MCP service, demonstrating various usage patterns from basic to advanced scenarios.

## Examples Overview

### 1. Basic Client (`basic-client.js`)
A simple client implementation showing:
- Connection management
- Basic tool calling
- Health checks
- Configuration retrieval
- Basic error handling

### 2. Advanced Client (`advanced-client.js`)
Advanced features including:
- Connection pooling and management
- Retry logic with exponential backoff
- Concurrent processing
- Performance monitoring
- Event-driven architecture
- Progress tracking

## Prerequisites

- Node.js 16+ 
- npm or yarn
- Running Docling MCP server (see main documentation)

## Installation

```bash
npm install
```

## Usage

### Basic Client
```bash
# Run the basic client example
npm start

# Or directly
node basic-client.js
```

### Advanced Client
```bash
# Run the advanced client example
node advanced-client.js
```

## Configuration

Both clients support various configuration options:

```javascript
const client = new DoclingMCPClient({
    serverUrl: 'http://localhost:3020/mcp',  // MCP server URL
    gatewayUrl: 'http://localhost:2091',     // MCP gateway URL
    timeout: 30000,                          // Request timeout (ms)
    maxConnections: 10,                      // Max concurrent connections
    retryAttempts: 3,                        // Number of retry attempts
    retryDelay: 1000,                        // Base retry delay (ms)
    enableMetrics: true                      // Enable performance metrics
});
```

## Features

### Connection Management
- Automatic connection handling
- Connection pooling (advanced client)
- Graceful disconnection
- Connection state monitoring

### Error Handling
- Comprehensive error catching
- Retry logic with exponential backoff
- Timeout handling
- Connection error recovery

### Performance Monitoring
- Request/response time tracking
- Error rate monitoring
- Throughput measurement
- Percentile calculations (P95, P99)

### Concurrent Processing
- Batch document processing
- Configurable concurrency limits
- Progress tracking
- Result aggregation

## API Reference

### Basic Client Methods

#### `connect()`
Establishes connection to the MCP server.

#### `disconnect()`
Closes connection to the server.

#### `callTool(toolName, arguments)`
Calls a specific tool on the MCP server.

#### `healthCheck()`
Performs a health check on the server.

#### `listTools()`
Lists available tools on the server.

#### `convertDocument(filePath, outputFormat)`
Converts a document to the specified format.

#### `processBatch(filePaths, outputFormat)`
Processes multiple documents in batch.

### Advanced Client Additional Methods

#### `convertDocumentsConcurrently(filePaths, outputFormat, maxConcurrency)`
Processes multiple documents concurrently with configurable concurrency.

#### `processBatchWithProgress(filePaths, outputFormat)`
Processes documents with progress tracking.

#### `getMetrics()`
Returns performance metrics.

#### `resetMetrics()`
Resets performance metrics.

## Events

The advanced client emits various events:

### `connecting`
Emitted when starting to connect to the server.

### `connected`
Emitted when successfully connected to the server.

### `disconnected`
Emitted when disconnected from the server.

### `error`
Emitted when an error occurs.

### `progress`
Emitted during batch processing to indicate progress.

### `metric`
Emitted when performance metrics are recorded.

## Error Handling

Both clients implement comprehensive error handling:

```javascript
try {
    await client.connect();
    const result = await client.convertDocument('/path/to/file.pdf', 'markdown');
    console.log('Conversion result:', result);
} catch (error) {
    console.error('Error:', error.message);
} finally {
    await client.disconnect();
}
```

## Performance Monitoring

Monitor client performance:

```javascript
// Get current metrics
const metrics = client.getMetrics();
console.log('Average response time:', metrics.avgResponseTime);
console.log('Error rate:', metrics.errorRate);
console.log('Throughput:', metrics.throughput);

// Reset metrics
client.resetMetrics();
```

## Testing

Run the test suite:

```bash
# Test basic client
node test-basic-client.js

# Test advanced client
node test-advanced-client.js

# Performance benchmarks
node performance-test.js
```

## Troubleshooting

### Connection Issues
- Ensure the MCP server is running
- Check server URL configuration
- Verify network connectivity

### Timeout Errors
- Increase timeout configuration
- Check server load and performance
- Monitor network latency

### Tool Call Failures
- Verify tool names and parameters
- Check server logs for errors
- Ensure documents exist and are accessible

## Best Practices

1. **Always disconnect** when done to free resources
2. **Use connection pooling** for high-throughput scenarios
3. **Implement retry logic** for production applications
4. **Monitor performance metrics** to optimize usage
5. **Handle errors gracefully** with appropriate user feedback
6. **Use concurrent processing** for batch operations
7. **Configure appropriate timeouts** based on your use case

## Integration Examples

### Express.js Integration
```javascript
const express = require('express');
const DoclingMCPClient = require('./basic-client');

const app = express();
const client = new DoclingMCPClient();

app.post('/convert', async (req, res) => {
    try {
        await client.connect();
        const result = await client.convertDocument(req.body.filePath, req.body.format);
        res.json({ success: true, result });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    } finally {
        await client.disconnect();
    }
});
```

### Worker Queue Integration
```javascript
const Queue = require('bull');
const DoclingMCPAdvancedClient = require('./advanced-client');

const conversionQueue = new Queue('document conversions');
const client = new DoclingMCPAdvancedClient();

conversionQueue.process(async (job) => {
    const { filePath, outputFormat } = job.data;
    return await client.convertDocument(filePath, outputFormat);
});
```

## Contributing

When adding new features or examples:
1. Follow existing code patterns and style
2. Add comprehensive error handling
3. Include performance considerations
4. Update documentation
5. Add appropriate tests

## License

See the main project LICENSE file for licensing information.