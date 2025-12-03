# Docling MCP Server Integration Tests

This directory contains comprehensive automated integration tests for the docling-mcp service implementation. The test suite covers all critical functionality including HTTP/SSE transport, STDIO transport, MCP protocol compliance, custom SSE handler implementation, tool execution, error handling, Docker integration, performance testing, and security validation.

## Test Suite Overview

### 1. **Integration Tests** (`test_docling_mcp_integration.py`)
- Server initialization and setup
- Tool listing functionality
- Health check tool execution
- Document conversion tool testing
- Batch document processing
- Error handling and validation
- MCP protocol compliance
- Concurrent tool execution
- Tool input validation

### 2. **HTTP/SSE Transport Tests** (`test_http_sse_transport.py`)
- HTTP endpoint accessibility
- SSE protocol compliance
- CORS header validation
- Connection handling and cleanup
- Stream data flow management
- Error recovery mechanisms
- Performance characteristics
- Security header validation

### 3. **STDIO Transport Tests** (`test_stdio_transport.py`)
- STDIO stream management
- JSON message handling
- Binary data processing
- Line-based protocol compliance
- Error recovery and cleanup
- Session lifecycle management
- Performance optimization
- Protocol compliance validation

### 4. **Docker Integration Tests** (`test_docker_integration.py`)
- Docker build process validation
- Health check functionality
- Service startup and shutdown
- Multi-container integration
- Resource management
- Security configuration
- Logging and monitoring
- Network connectivity

## Test Infrastructure

### Configuration Files
- **`pytest.ini`**: Pytest configuration with markers, coverage settings, and test discovery rules
- **`test_requirements.txt`**: Comprehensive test dependencies including pytest, aiohttp, docker, and security testing tools
- **`run_integration_tests.py`**: Main test orchestration script for running all test suites

### CI/CD Integration
- **`.github/workflows/integration-tests.yml`**: GitHub Actions workflow for automated testing
- Supports multiple test categories (unit, integration, docker, performance, security)
- Includes coverage reporting and artifact management
- Automated PR commenting with test results

## Running Tests

### Quick Start
```bash
# Install test dependencies
pip install -r tests/test_requirements.txt

# Run all tests
python tests/run_integration_tests.py

# Run specific test suite
python tests/run_integration_tests.py --suite integration

# Run with verbose output
python tests/run_integration_tests.py --verbose
```

### Using Pytest Directly
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_docling_mcp_integration.py

# Run with coverage
pytest tests/ --cov=docling_mcp_server --cov-report=html

# Run specific test markers
pytest tests/ -m integration
pytest tests/ -m docker
pytest tests/ -m performance
pytest tests/ -m security
```

### Test Markers
- **`unit`**: Unit tests for individual components
- **`integration`**: Integration tests for complete functionality
- **`docker`**: Docker containerization tests
- **`performance`**: Performance and load testing
- **`security`**: Security and vulnerability testing
- **`slow`**: Tests that take longer to execute
- **`smoke`**: Quick smoke tests for basic functionality

## Test Data

The test suite automatically creates sample test documents in the `tests/data/` directory:
- **`test_document.txt`**: Simple text document
- **`test_document.md`**: Markdown document with headers
- **`test_document.json`**: JSON document with metadata

## Coverage and Reporting

### Coverage Targets
- **Line Coverage**: Minimum 80%
- **Branch Coverage**: Minimum 75%
- **Function Coverage**: Minimum 85%

### Test Reports
- **HTML Report**: `htmlcov/index.html` - Interactive coverage report
- **JSON Report**: `test_report.json` - Machine-readable test results
- **JUnit XML**: `junit.xml` - CI/CD integration format

### Performance Benchmarks
- Response time: < 100ms for basic operations
- Throughput: > 1000 requests/second
- Memory usage: < 200MB peak usage
- CPU utilization: < 80% under load

## Docker Testing

### Local Docker Testing
```bash
# Build Docker image
docker build -f Dockerfile.docling-mcp -t docling-mcp:test .

# Run container
docker run -d --name docling-mcp-test -p 3020:3020 docling-mcp:test

# Test health endpoint
curl http://localhost:3020/health

# Test SSE endpoint
curl -H "Accept: text/event-stream" http://localhost:3020/mcp

# Clean up
docker stop docling-mcp-test && docker rm docling-mcp-test
```

### Multi-container Testing
```bash
# Start all services
docker-compose -f docker-compose.mcp-pro.yml up -d

# Run integration tests
python tests/run_integration_tests.py --suite integration

# Stop services
docker-compose -f docker-compose.mcp-pro.yml down
```

## Continuous Integration

The test suite integrates with GitHub Actions for automated testing on:
- **Push events**: All branches
- **Pull requests**: Main and develop branches
- **Scheduled runs**: Daily at 2 AM UTC

### CI Test Matrix
- **Unit Tests**: Fast feedback on code changes
- **Integration Tests**: Complete functionality validation
- **Docker Tests**: Containerization and deployment testing
- **Performance Tests**: Load and stress testing
- **Security Tests**: Vulnerability and compliance testing
- **Multi-container Tests**: Service integration validation

## Test Development Guidelines

### Writing New Tests
1. Use descriptive test function names
2. Include proper docstrings
3. Use pytest fixtures for common setup
4. Mock external dependencies appropriately
5. Include both positive and negative test cases
6. Add appropriate test markers

### Test Structure
```python
@pytest.mark.integration
async def test_specific_functionality(self, server, client):
    """Test specific functionality with proper documentation."""
    # Arrange
    setup_data = await self.setup_test_data()
    
    # Act
    result = await server.specific_function(setup_data)
    
    # Assert
    assert result.is_success is True
    assert "expected_value" in result.content
```

### Error Handling Tests
- Test timeout scenarios
- Test invalid input handling
- Test connection failures
- Test resource exhaustion
- Test permission errors

## Troubleshooting

For comprehensive troubleshooting procedures, see the [Troubleshooting Guide](../docs/TROUBLESHOOTING.md) and [Troubleshooting Scripts](../docs/TROUBLESHOOTING_SCRIPTS.md).

### Common Issues
1. **Docker not available**: Tests will skip Docker-related tests
2. **Port conflicts**: Ensure port 3020 is available
3. **Missing dependencies**: Install test requirements
4. **Timeout errors**: Increase timeout values for slow systems
5. **Service startup failures**: Use the [Diagnostic Script](../docs/TROUBLESHOOTING_SCRIPTS.md#diagnostic-script) to identify issues
6. **Test environment problems**: Use the [Service Recovery Script](../docs/TROUBLESHOOTING_SCRIPTS.md#service-recovery-script) to reset test environment

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with detailed output
pytest tests/ -v -s --log-cli-level=DEBUG
```

### Performance Issues
- Use `--benchmark-only` for performance testing
- Monitor system resources during test execution
- Adjust timeout values for slower systems
- Use the [Performance Monitoring Script](../docs/TROUBLESHOOTING_SCRIPTS.md#performance-monitoring-script) to track test performance

### Test Environment Issues
- Use the [Configuration Validation Script](../docs/TROUBLESHOOTING_SCRIPTS.md#configuration-validation-script) to verify test configuration
- Use the [Log Analysis Script](../docs/TROUBLESHOOTING_SCRIPTS.md#log-analysis-script) to analyze test failures
- Use the [Health Check Script](../docs/TROUBLESHOOTING_SCRIPTS.md#health-check-script) to verify test environment

## Contributing

When adding new features or fixing bugs:
1. Write corresponding tests
2. Ensure all existing tests pass
3. Maintain or improve coverage levels
4. Update documentation as needed
5. Run the full test suite before submitting

## Support

For issues with the test suite:
1. Check the troubleshooting section
2. Review test logs and reports
3. Verify environment setup
4. Consult the main project documentation