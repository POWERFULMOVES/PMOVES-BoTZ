# Docling MCP Server Configuration Guide

This guide provides comprehensive documentation for the configuration management system of the Docling MCP Server.

## Overview

The Docling MCP Server now supports externalized configuration through YAML files, environment variables, and command-line arguments. This provides flexibility for different deployment scenarios while maintaining backward compatibility.

## Configuration Architecture

The configuration system follows a hierarchical approach:

1. **Default Configuration** (`config/default.yaml`) - Base settings
2. **Environment Configuration** (`config/development.yaml`, `config/production.yaml`) - Environment-specific overrides
3. **Environment Variables** - Runtime overrides using `DOCLING_MCP_*` prefix
4. **Command Line Arguments** - Highest priority overrides

## Configuration Files

### Directory Structure
```
pmoves_multi_agent_pro_pack/
├── config/
│   ├── __init__.py
│   ├── loader.py
│   ├── schema.py
│   ├── config_schema.json
│   ├── default.yaml
│   ├── development.yaml
│   └── production.yaml
```

### Configuration Files

#### `default.yaml`
Contains all default values and serves as the base configuration. This file should not be modified in production.

#### `development.yaml`
Development-specific overrides with more verbose logging, longer timeouts, and relaxed security settings.

#### `production.yaml`
Production-specific configuration with optimized performance, security hardening, and production-ready settings.

## Configuration Categories

### 1. Server Configuration
```yaml
server:
  host: "0.0.0.0"          # Server bind address
  port: 3020               # Server port
  transport: "http"        # Transport type: stdio or http
  name: "docling-mcp"      # Server name
```

### 2. Logging Configuration
```yaml
logging:
  level: "INFO"            # Log level: DEBUG, INFO, WARNING, ERROR
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  name: "docling-mcp"      # Logger name
  output: "stdout"         # Output: stdout, stderr, or file path
```

### 3. SSE (Server-Sent Events) Configuration
```yaml
sse:
  endpoint: "/mcp"         # SSE endpoint path
  keepalive_interval: 0.1  # Keepalive interval in seconds
  connection_timeout: 30.0 # Connection timeout in seconds
  max_queue_size: 1000     # Maximum queue size
  cors_origins: ["*"]      # CORS allowed origins
  cors_methods: ["GET", "OPTIONS"]
  cors_headers: ["Content-Type", "Accept", "Cache-Control"]
  cors_max_age: 86400      # CORS max age in seconds (24 hours)
```

### 4. Performance Configuration
```yaml
performance:
  tool_timeout: 30.0       # Tool execution timeout in seconds
  max_connections: 100     # Maximum number of concurrent connections
  rate_limit_requests: 1000 # Rate limit requests per window
  rate_limit_window: 3600  # Rate limit window in seconds
```

### 5. Security Configuration
```yaml
security:
  enable_cors: true        # Enable CORS
  allowed_origins: ["*"]   # Allowed origins for CORS
  enable_rate_limiting: false # Enable rate limiting
  max_request_size: 10485760 # Maximum request size in bytes (10MB)
```

### 6. Docling Integration Configuration
```yaml
docling:
  cache_dir: "/data/cache" # Cache directory path
  enable_cache: true       # Enable caching
  max_file_size: 104857600 # Maximum file size in bytes (100MB)
  supported_formats:       # Supported document formats
    - "pdf"
    - "docx"
    - "pptx"
    - "xlsx"
    - "html"
    - "txt"
    - "md"
  pipeline_options: {}     # Additional Docling pipeline options
```

### 7. Health Check Configuration
```yaml
health_check:
  endpoint: "/health"      # Health check endpoint path
  interval: 30             # Health check interval in seconds
  timeout: 10              # Health check timeout in seconds
  retries: 3               # Number of health check retries
  start_period: 30         # Health check start period in seconds
```

## Environment Variables

Environment variables provide runtime configuration overrides using the `DOCLING_MCP_` prefix. Use double underscores for nested configuration.

### Examples:
```bash
# Server configuration
DOCLING_MCP_SERVER__HOST=0.0.0.0
DOCLING_MCP_SERVER__PORT=3020
DOCLING_MCP_SERVER__TRANSPORT=http

# Logging configuration
DOCLING_MCP_LOGGING__LEVEL=DEBUG
DOCLING_MCP_LOGGING__OUTPUT=/var/log/docling-mcp.log

# Performance configuration
DOCLING_MCP_PERFORMANCE__TOOL_TIMEOUT=60.0
DOCLING_MCP_PERFORMANCE__MAX_CONNECTIONS=200

# Security configuration
DOCLING_MCP_SECURITY__ENABLE_CORS=true
DOCLING_MCP_SECURITY__ALLOWED_ORIGINS=https://your-domain.com,https://app.your-domain.com

# SSE configuration
DOCLING_MCP_SSE__KEEPALIVE_INTERVAL=0.5
DOCLING_MCP_SSE__CONNECTION_TIMEOUT=45.0
```

## Command Line Arguments

Command line arguments provide the highest priority configuration overrides:

```bash
# Basic usage
python docling_mcp_server.py --environment production

# Transport configuration
python docling_mcp_server.py --transport http --host 0.0.0.0 --port 8080

# Logging configuration
python docling_mcp_server.py --log-level DEBUG

# Custom configuration file
python docling_mcp_server.py --config-file /path/to/config.yaml

# Create default configuration files
python docling_mcp_server.py --create-config
```

## Docker Deployment

### Basic Docker Usage
```bash
# Build the image
docker build -f Dockerfile.docling-mcp -t docling-mcp .

# Run with default configuration
docker run -p 3020:3020 docling-mcp

# Run with environment variables
docker run -p 3020:3020 \
  -e DOCLING_MCP_LOGGING__LEVEL=DEBUG \
  -e DOCLING_MCP_SERVER__PORT=8080 \
  docling-mcp

# Run with custom configuration
docker run -p 3020:3020 \
  -v /path/to/config.yaml:/srv/config/custom.yaml:ro \
  docling-mcp --config-file /srv/config/custom.yaml
```

### Docker Compose Usage

#### Development Environment
```bash
# Use development configuration
docker-compose -f docker-compose.mcp-pro.yml -f docker-compose.development.yml up docling-mcp

# Or set environment explicitly
export DOCLING_MCP_ENVIRONMENT=development
docker-compose -f docker-compose.mcp-pro.yml up docling-mcp
```

#### Production Environment
```bash
# Use production configuration
docker-compose -f docker-compose.mcp-pro.yml -f docker-compose.production.yml up docling-mcp

# Or set environment explicitly
export DOCLING_MCP_ENVIRONMENT=production
docker-compose -f docker-compose.mcp-pro.yml up docling-mcp
```

## Configuration Validation

The configuration system validates all settings at startup. Common validation errors include:

- Invalid port numbers (must be 1-65535)
- Negative timeout values
- Empty required fields
- Invalid log levels
- Invalid transport types

## Best Practices

### Development
- Use DEBUG logging level
- Enable verbose error messages
- Use longer timeouts for debugging
- Allow broader CORS origins for local development

### Production
- Use WARNING or ERROR logging level
- Specify explicit CORS origins (avoid "*")
- Enable rate limiting
- Use appropriate resource limits
- Configure proper health check intervals
- Set up log rotation for file outputs

### Security
- Never use wildcard CORS origins in production
- Enable rate limiting for public deployments
- Set appropriate file size limits
- Use secure transport (HTTPS) when possible
- Regularly review and update security settings

## Troubleshooting

For comprehensive troubleshooting procedures, see the [Troubleshooting Guide](../docs/TROUBLESHOOTING.md) and [Troubleshooting Scripts](../docs/TROUBLESHOOTING_SCRIPTS.md).

### Configuration Loading Issues
1. Check file permissions on configuration files
2. Verify YAML syntax is valid
3. Ensure environment variable names are correct
4. Check for conflicting command line arguments
5. Use the [Configuration Validation Script](../docs/TROUBLESHOOTING_SCRIPTS.md#configuration-validation-script) to validate your configuration

### Performance Issues
1. Adjust `tool_timeout` for long-running operations
2. Increase `max_connections` for high-traffic scenarios
3. Optimize `keepalive_interval` for SSE connections
4. Configure appropriate rate limiting
5. Use the [Performance Monitoring Script](../docs/TROUBLESHOOTING_SCRIPTS.md#performance-monitoring-script) to track performance metrics

### Security Issues
1. Review CORS configuration
2. Check rate limiting settings
3. Verify file size limits
4. Review allowed origins
5. Use the [Diagnostic Script](../docs/TROUBLESHOOTING_SCRIPTS.md#diagnostic-script) for comprehensive security analysis

## Migration from Hardcoded Configuration

If you're migrating from the previous hardcoded version:

1. The server will work with default configuration if no config files are present
2. Command line arguments maintain backward compatibility
3. Environment variables provide easy migration path
4. Gradually move to YAML configuration files for better organization

## Configuration Examples

### Minimal Development Configuration
```yaml
server:
  transport: http
  port: 3020

logging:
  level: DEBUG

security:
  enable_cors: true
  allowed_origins: ["http://localhost:*"]
```

### Production-Ready Configuration
```yaml
server:
  transport: http
  host: 0.0.0.0
  port: 3020

logging:
  level: WARNING
  output: /var/log/docling-mcp.log

performance:
  tool_timeout: 30.0
  max_connections: 200
  rate_limit_requests: 500
  rate_limit_window: 3600

security:
  enable_cors: true
  allowed_origins: ["https://your-domain.com"]
  enable_rate_limiting: true
  max_request_size: 52428800

health_check:
  interval: 60
  timeout: 15
  retries: 5
```

## Advanced Configuration

### Custom Pipeline Options
```yaml
docling:
  pipeline_options:
    ocr_options:
      enabled: true
      language: "eng"
    table_structure_options:
      enabled: true
```

### Multiple Output Formats
The server supports multiple document output formats that can be configured through the tool schema, which is automatically generated based on the configuration.

## Support

For configuration-related issues:
1. Check the validation errors in the logs
2. Verify file permissions and paths
3. Review the configuration schema in `config/config_schema.json`
4. Use the `--create-config` flag to generate template files
5. Consult the troubleshooting section above