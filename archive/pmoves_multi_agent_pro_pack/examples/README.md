# Docling MCP Client Examples

This directory contains comprehensive client examples for the Docling MCP (Model Context Protocol) service. These examples demonstrate how to integrate document processing capabilities into various applications and environments.

## Overview

The Docling MCP service provides document conversion and processing capabilities through the Model Context Protocol. It supports:
- Document conversion (PDF, DOCX, PPTX, XLSX, HTML, TXT, MD to Markdown/Text/JSON)
- Batch document processing
- Real-time streaming via Server-Sent Events (SSE)
- Health monitoring and metrics
- Multiple transport protocols (HTTP, STDIO)

## Directory Structure

```
examples/
├── javascript/           # JavaScript/TypeScript examples
│   ├── browser/         # Browser-based clients
│   ├── nodejs/          # Node.js server and CLI clients
│   └── frameworks/      # Framework integrations (React, Vue, Angular)
├── python/              # Python client examples
│   ├── basic/           # Basic usage examples
│   ├── advanced/        # Advanced features and patterns
│   └── frameworks/      # Framework integrations (FastAPI, Django)
├── curl/                # Command-line examples using curl
├── go/                  # Go client examples
├── java/                # Java client examples
├── mcp-library/         # MCP client library usage examples
├── sse-clients/         # Custom SSE client implementations
├── testing/             # Testing utilities and mock servers
├── performance/         # Performance benchmarking tools
├── real-world/          # Real-world integration examples
└── docs/                # Additional documentation
```

## Quick Start

### Prerequisites

- Docker and Docker Compose (for running the service)
- Node.js 16+ (for JavaScript examples)
- Python 3.8+ (for Python examples)
- Go 1.19+ (for Go examples)
- Java 11+ (for Java examples)

### Running the Service

```bash
# Start the Docling MCP service
cd pmoves_multi_agent_pro_pack
docker-compose -f docker-compose.mcp-pro.yml up docling-mcp

# Test the service
curl -N -H "Accept: text/event-stream" http://localhost:3020/mcp
```

### Basic Usage Examples

#### JavaScript/TypeScript
```javascript
// Connect to the MCP service
const client = new MCPClient('http://localhost:3020/mcp');

// Convert a document
const result = await client.callTool('convert_document', {
  file_path: '/path/to/document.pdf',
  output_format: 'markdown'
});
```

#### Python
```python
from mcp_client import MCPClient

# Connect to the service
client = MCPClient('http://localhost:3020/mcp')

# Convert a document
result = client.call_tool('convert_document', {
    'file_path': '/path/to/document.pdf',
    'output_format': 'markdown'
})
```

#### curl
```bash
# Health check
curl http://localhost:3020/health

# Convert document (via MCP gateway)
curl -X POST http://localhost:2091/tools/convert_document \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/path/to/document.pdf", "output_format": "markdown"}'
```

## Examples by Category

### Basic Usage
- **Simple Document Conversion**: Convert single documents to different formats
- **Health Monitoring**: Check service health and capabilities
- **Configuration Management**: Get and manage server configuration

### Advanced Features
- **Batch Processing**: Process multiple documents efficiently
- **Streaming Conversion**: Real-time document processing with SSE
- **Error Handling**: Robust error handling and retry mechanisms
- **Connection Management**: Connection pooling and lifecycle management

### Framework Integration
- **React Integration**: Document processing in React applications
- **Vue.js Integration**: Vue components for document handling
- **Angular Integration**: Angular services for document conversion
- **Express.js Integration**: Backend integration with Express
- **FastAPI Integration**: High-performance Python backend integration
- **Django Integration**: Django app integration examples

### Enterprise Features
- **Authentication & Security**: Secure client implementations
- **Performance Optimization**: High-performance client patterns
- **Monitoring & Observability**: Client-side metrics and logging
- **Resilience Patterns**: Circuit breakers and fallback mechanisms

### Real-World Scenarios
- **Document Management System**: Complete DMS integration
- **Content Processing Pipeline**: Automated content workflows
- **Search & Indexing**: Document indexing for search systems
- **Analytics Dashboard**: Document processing analytics
- **Mobile App Integration**: Mobile client examples

## Configuration

Each example includes its own configuration files and setup instructions. See individual README files in each directory for specific setup requirements.

## Testing

Run the test suite to verify all examples work correctly:

```bash
cd examples/testing
npm test          # JavaScript tests
python test_all.py # Python tests
go test          # Go tests
```

## Contributing

When adding new examples:
1. Follow the existing directory structure
2. Include comprehensive documentation
3. Add appropriate tests
4. Update this README with new examples
5. Ensure examples are production-ready

## Support

For issues and questions:
- Check the troubleshooting section in each example
- Review the main documentation in `/docs`
- Check the service logs for connectivity issues
- Verify your environment setup

## License

See the main project LICENSE file for licensing information.