# MCP Server Implementation Remediation Plan

## Executive Summary

This document provides a comprehensive remediation plan for resolving critical issues in the MCP (Model Context Protocol) server implementation within the PMOVES Multi-Agent Pro Pack. The current implementation has several fundamental problems that prevent proper startup, HTTP transport functionality, and integration with the MCP gateway.

## Current Issues Analysis

### 1. Docling-MCP Server Implementation Bugs

**Critical Issues Identified:**

1. **Incorrect MCP Server API Usage**: The current implementation uses deprecated or incorrect MCP server API patterns
2. **Improper HTTP Transport Implementation**: The SSE (Server-Sent Events) transport is not correctly implemented
3. **Missing Proper Initialization**: The server fails to properly initialize with the MCP protocol requirements
4. **Docker Configuration Issues**: The Dockerfile has dependency and startup problems

**Specific Technical Problems:**

- **File**: [`docling_mcp_server.py`](pmoves_multi_agent_pro_pack/docling_mcp_server.py:270)
  - Incorrect parameter order in `server.run()` method
  - Missing proper transport initialization
  - Improper SSE transport setup

- **File**: [`Dockerfile.docling-mcp`](pmoves_multi_agent_pro_pack/Dockerfile.docling-mcp:36)
  - Health check uses incorrect endpoint format
  - Missing proper dependency validation
  - Incorrect startup command sequence

### 2. MCP Gateway Integration Issues

**Problems Identified:**

1. **Catalog Configuration**: The [`mcp_catalog.yaml`](pmoves_multi_agent_pro_pack/mcp_catalog.yaml:1) may have incorrect server definitions
2. **Connection Timeouts**: Inadequate timeout settings for service dependencies
3. **Health Check Failures**: Services failing health checks due to improper startup

### 3. Missing MCP Protocol Compliance

**Compliance Gaps:**

1. **HTTP Transport Standards**: Not following official MCP HTTP transport specifications
2. **Streaming Support**: Missing proper Server-Sent Events implementation
3. **Client Capability**: Server doesn't properly advertise client capabilities
4. **Error Handling**: Inadequate error handling and reporting

## Resolution Strategy

### Phase 1: Fix Core MCP Server Implementation

#### 1.1 Update MCP Server API Usage

**Action Items:**
- Update to use proper MCP 1.0+ API patterns
- Fix parameter order in server initialization
- Implement correct transport initialization

**Code Changes Required:**
```python
# Current incorrect implementation (line 270-272)
await server.server.run(
    transport,
    server.server.create_initialization_options()
)

# Correct implementation
await server.server.run(
    read_stream,  # or proper transport streams
    write_stream,
    server.server.create_initialization_options()
)
```

#### 1.2 Fix HTTP Transport Implementation

**Action Items:**
- Implement proper SSE transport using official MCP patterns
- Add correct endpoint handling
- Implement proper streaming support

**Implementation Pattern:**
```python
from mcp.server.sse import SseServerTransport
from mcp.server import Server

async def run_http_server(host: str = "0.0.0.0", port: int = 3020):
    server = DoclingMCPServer()
    server.setup_handlers()
    
    # Create proper SSE transport
    transport = SseServerTransport(f"http://{host}:{port}/mcp")
    
    # Start the transport (this handles HTTP server setup)
    await transport.start_server(
        host=host,
        port=port,
        handle_mcp_session=lambda streams: server.server.run(
            streams[0],  # read_stream
            streams[1],  # write_stream
            server.server.create_initialization_options()
        )
    )
```

#### 1.3 Update Docker Configuration

**Action Items:**
- Fix health check endpoint
- Update dependency installation order
- Correct startup command

**Dockerfile Updates:**
```dockerfile
# Fix health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:3020/mcp || exit 1

# Update startup command
CMD ["python", "docling_mcp_server.py", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "3020"]
```

### Phase 2: Implement Proper MCP Protocol Compliance

#### 2.1 HTTP Transport Standards

**Requirements:**
- Implement official MCP HTTP transport specification
- Support both SSE and WebSocket transports
- Proper Content-Type headers for SSE

**Implementation:**
```python
# Proper SSE headers
headers = {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Access-Control-Allow-Origin": "*"
}
```

#### 2.2 Streaming Support

**Requirements:**
- Implement Server-Sent Events properly
- Handle connection lifecycle correctly
- Support reconnection patterns

#### 2.3 Client Capability Implementation

**Requirements:**
- Properly advertise server capabilities
- Handle client initialization correctly
- Support capability negotiation

### Phase 3: Fix Integration Issues

#### 3.1 Update Service Dependencies

**Action Items:**
- Fix service dependency order in docker-compose
- Update health check dependencies
- Configure proper startup timeouts

#### 3.2 Fix Catalog Configuration

**Updates to [`mcp_catalog.yaml`](pmoves_multi_agent_pro_pack/mcp_catalog.yaml:1):**
```yaml
servers:
  docling:
    type: http
    url: http://docling-mcp:3020/mcp  # Add proper endpoint
    timeout: 60  # Increase timeout
    retries: 5   # Increase retries
    headers:
      Content-Type: application/json
```

### Phase 4: Testing and Validation

#### 4.1 Create Comprehensive Test Suite

**Test Categories:**
1. **Unit Tests**: Individual component testing
2. **Integration Tests**: Service-to-service communication
3. **End-to-End Tests**: Full workflow testing
4. **Performance Tests**: Load and stress testing

#### 4.2 Validation Procedures

**Validation Steps:**
1. Verify MCP server starts without errors
2. Test HTTP transport connectivity
3. Validate SSE streaming functionality
4. Test integration with MCP gateway
5. Verify tool execution capabilities

## Implementation Timeline

### Week 1: Core Fixes
- **Days 1-2**: Fix MCP server API usage
- **Days 3-4**: Implement proper HTTP transport
- **Days 5-7**: Update Docker configuration

### Week 2: Protocol Compliance
- **Days 8-10**: Implement MCP protocol standards
- **Days 11-12**: Add streaming support
- **Days 13-14**: Client capability implementation

### Week 3: Integration and Testing
- **Days 15-17**: Fix integration issues
- **Days 18-19**: Create test suite
- **Days 20-21**: Comprehensive testing and validation

## Success Criteria

### Technical Success Metrics

1. **MCP Server Startup**: Server starts without errors within 30 seconds
2. **HTTP Transport**: Successfully handles HTTP requests on port 3020
3. **SSE Streaming**: Maintains stable SSE connections for >5 minutes
4. **Tool Execution**: Successfully executes document conversion tools
5. **Gateway Integration**: MCP gateway successfully connects and routes requests

### Performance Metrics

1. **Response Time**: Tool calls respond within 10 seconds
2. **Connection Stability**: 99% uptime over 24-hour period
3. **Memory Usage**: <500MB memory consumption under normal load
4. **CPU Usage**: <50% CPU utilization during document processing

### Integration Success

1. **Service Dependencies**: All services start in correct order
2. **Health Checks**: All health checks pass consistently
3. **End-to-End Flow**: Complete document processing workflow works
4. **Error Handling**: Graceful error handling and recovery

## Risk Mitigation

### High-Risk Items

1. **MCP Protocol Changes**: Monitor for MCP specification updates
2. **Dependency Conflicts**: Version compatibility between MCP and docling
3. **Docker Networking**: Complex networking between services

### Mitigation Strategies

1. **Version Pinning**: Pin specific versions of MCP and dependencies
2. **Rollback Plan**: Maintain previous working configuration
3. **Staged Deployment**: Deploy changes incrementally
4. **Monitoring**: Implement comprehensive logging and monitoring

## Documentation Requirements

### Updated Documentation

1. **README_PRO.md**: Update with current status and known issues
2. **Setup Guide**: Create comprehensive setup instructions
3. **Troubleshooting Guide**: Document common issues and solutions
4. **API Documentation**: Document MCP server API endpoints

### New Documentation

1. **MCP Protocol Guide**: Reference to official MCP documentation
2. **Implementation Patterns**: Code examples and best practices
3. **Testing Procedures**: Comprehensive testing documentation
4. **Deployment Guide**: Production deployment instructions

## Verification Checklist

### Pre-Deployment Verification

- [ ] MCP server starts without errors
- [ ] HTTP transport responds to requests
- [ ] SSE streaming works correctly
- [ ] Tool execution functions properly
- [ ] Docker health checks pass
- [ ] Integration with MCP gateway works
- [ ] All services start in correct order
- [ ] Error handling works correctly

### Post-Deployment Verification

- [ ] 24-hour stability test passes
- [ ] Performance metrics meet requirements
- [ ] All integration points work
- [ ] Documentation is complete and accurate
- [ ] Monitoring and logging work correctly
- [ ] Rollback procedures tested

## Conclusion

This remediation plan provides a systematic approach to resolving the MCP server implementation issues. By following this plan, we can achieve a fully functional MCP Pro setup that meets all requirements and provides reliable service for the PMOVES Multi-Agent system.

The plan prioritizes critical fixes first, ensures proper testing at each stage, and provides clear success criteria for validation. Regular monitoring and documentation updates will ensure long-term maintainability and support for future enhancements.
