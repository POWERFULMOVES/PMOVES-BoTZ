# Configuration System Update for Docling MCP Server

## Overview

The Docling MCP Server has been updated with a comprehensive configuration management system that externalizes all hardcoded values into configurable YAML files. This provides better deployment flexibility, maintainability, and environment-specific customization.

## What's New

### 🎯 **Configuration Management System**
- **Externalized Configuration**: All hardcoded values moved to YAML configuration files
- **Environment Support**: Separate configurations for development, production, and custom environments
- **Environment Variables**: Runtime configuration overrides using `DOCLING_MCP_*` prefix
- **Command Line Interface**: Enhanced CLI with configuration options
- **Configuration Validation**: Built-in validation with detailed error messages

### 📁 **New Configuration Structure**
```
pmoves_multi_agent_pro_pack/
├── config/
│   ├── __init__.py              # Configuration package
│   ├── loader.py                # Configuration loading logic
│   ├── schema.py                # Configuration schema and validation
│   ├── config_schema.json       # JSON schema for validation
│   ├── default.yaml             # Base configuration
│   ├── development.yaml         # Development overrides
│   └── production.yaml          # Production overrides
├── docker-compose.development.yml   # Development Docker setup
├── docker-compose.production.yml    # Production Docker setup
└── tests/test_configuration.py      # Configuration test suite
```

### 🔧 **Configuration Categories**

1. **Server Settings**: Host, port, transport type, server name
2. **Logging Configuration**: Level, format, output destination
3. **SSE Handler Settings**: Queue sizes, timeouts, keepalive intervals, CORS settings
4. **Performance Settings**: Max connections, rate limits, tool timeouts
5. **Security Settings**: CORS origins, rate limiting, request size limits
6. **Docling Integration**: Cache paths, processing options, file size limits
7. **Health Check Settings**: Endpoints, intervals, timeouts, retries

## Quick Start

### Using Default Configuration
```bash
# Run with default settings
python docling_mcp_server.py

# Run with HTTP transport
python docling_mcp_server.py --transport http --host 0.0.0.0 --port 3020
```

### Using Environment-Specific Configuration
```bash
# Development environment
python docling_mcp_server.py --environment development

# Production environment
python docling_mcp_server.py --environment production
```

### Using Environment Variables
```bash
# Set configuration via environment variables
export DOCLING_MCP_SERVER__PORT=8080
export DOCLING_MCP_LOGGING__LEVEL=DEBUG
export DOCLING_MCP_SECURITY__ENABLE_RATE_LIMITING=true

python docling_mcp_server.py
```

### Using Custom Configuration File
```bash
# Use custom configuration file
python docling_mcp_server.py --config-file /path/to/config.yaml
```

## Docker Deployment

### Development Environment
```bash
# Run with development configuration
docker-compose -f docker-compose.mcp-pro.yml -f docker-compose.development.yml up docling-mcp

# Or set environment variable
export DOCLING_MCP_ENVIRONMENT=development
docker-compose -f docker-compose.mcp-pro.yml up docling-mcp
```

### Production Environment
```bash
# Run with production configuration
docker-compose -f docker-compose.mcp-pro.yml -f docker-compose.production.yml up docling-mcp

# Or set environment variable
export DOCLING_MCP_ENVIRONMENT=production
docker-compose -f docker-compose.mcp-pro.yml up docling-mcp
```

## Configuration Examples

### Development Configuration (`config/development.yaml`)
```yaml
logging:
  level: "DEBUG"  # Verbose logging for development

performance:
  tool_timeout: 60.0  # Longer timeout for debugging
  max_connections: 50

security:
  enable_cors: true
  allowed_origins:
    - "http://localhost:*"
    - "https://localhost:*"
  enable_rate_limiting: false  # Disabled for development
```

### Production Configuration (`config/production.yaml`)
```yaml
logging:
  level: "WARNING"  # Less verbose logging
  output: "/var/log/docling-mcp.log"  # File logging

performance:
  tool_timeout: 30.0
  max_connections: 200
  rate_limit_requests: 500
  rate_limit_window: 3600

security:
  enable_cors: true
  allowed_origins:  # Specify actual origins
    - "https://your-domain.com"
    - "https://app.your-domain.com"
  enable_rate_limiting: true
  max_request_size: 52428800  # 50MB
```

## Migration Guide

### From Hardcoded Configuration

If you're currently using the server with hardcoded values, the migration is seamless:

1. **Backward Compatibility**: All existing command-line arguments continue to work
2. **Default Behavior**: If no configuration files are present, the server uses sensible defaults
3. **Gradual Migration**: You can gradually move to YAML configuration files
4. **Environment Variables**: Use environment variables for quick overrides during migration

### Step-by-Step Migration

1. **Start with Environment Variables** (Quick Override)
   ```bash
   export DOCLING_MCP_LOGGING__LEVEL=DEBUG
   export DOCLING_MCP_SERVER__PORT=8080
   python docling_mcp_server.py
   ```

2. **Create Custom Configuration File**
   ```bash
   # Generate template files
   python docling_mcp_server.py --create-config
   
   # Edit the configuration
   nano config/custom.yaml
   ```

3. **Use Custom Configuration**
   ```bash
   python docling_mcp_server.py --config-file config/custom.yaml
   ```

4. **Move to Environment-Specific Configs**
   ```bash
   # Copy and customize environment files
   cp config/development.yaml config/staging.yaml
   nano config/staging.yaml
   
   # Use the environment
   python docling_mcp_server.py --environment staging
   ```

## Key Benefits

### 🚀 **Deployment Flexibility**
- **Multiple Environments**: Easy switching between dev, staging, production
- **Container-Friendly**: Optimized for Docker and Kubernetes deployments
- **Cloud-Native**: Supports 12-factor app principles

### 🔒 **Security Improvements**
- **No Hardcoded Secrets**: All sensitive values externalized
- **Environment Isolation**: Separate configs for different security contexts
- **Audit Trail**: Configuration changes can be tracked in version control

### 📊 **Operational Excellence**
- **Centralized Configuration**: Single source of truth for all settings
- **Validation**: Built-in validation prevents misconfigurations
- **Documentation**: Self-documenting configuration files
- **Troubleshooting**: Easier to diagnose configuration-related issues

### 🛠️ **Developer Experience**
- **Hot Reloading**: Configuration changes without code changes
- **IDE Support**: YAML files with schema validation
- **Testing**: Easy to test different configurations
- **Debugging**: Clear error messages for invalid configurations

## Configuration Reference

### Server Settings
| Parameter | Environment Variable | Default | Description |
|-----------|---------------------|---------|-------------|
| `host` | `DOCLING_MCP_SERVER__HOST` | `0.0.0.0` | Server bind address |
| `port` | `DOCLING_MCP_SERVER__PORT` | `3020` | Server port |
| `transport` | `DOCLING_MCP_SERVER__TRANSPORT` | `stdio` | Transport type (stdio/http) |
| `name` | `DOCLING_MCP_SERVER__NAME` | `docling-mcp` | Server name |

### Logging Configuration
| Parameter | Environment Variable | Default | Description |
|-----------|---------------------|---------|-------------|
| `level` | `DOCLING_MCP_LOGGING__LEVEL` | `INFO` | Log level (DEBUG/INFO/WARNING/ERROR) |
| `format` | `DOCLING_MCP_LOGGING__FORMAT` | Standard format | Log message format |
| `output` | `DOCLING_MCP_LOGGING__OUTPUT` | `stdout` | Output destination |

### Performance Settings
| Parameter | Environment Variable | Default | Description |
|-----------|---------------------|---------|-------------|
| `tool_timeout` | `DOCLING_MCP_PERFORMANCE__TOOL_TIMEOUT` | `30.0` | Tool execution timeout (seconds) |
| `max_connections` | `DOCLING_MCP_PERFORMANCE__MAX_CONNECTIONS` | `100` | Maximum concurrent connections |
| `rate_limit_requests` | `DOCLING_MCP_PERFORMANCE__RATE_LIMIT_REQUESTS` | `1000` | Rate limit per window |
| `rate_limit_window` | `DOCLING_MCP_PERFORMANCE__RATE_LIMIT_WINDOW` | `3600` | Rate limit window (seconds) |

### Security Settings
| Parameter | Environment Variable | Default | Description |
|-----------|---------------------|---------|-------------|
| `enable_cors` | `DOCLING_MCP_SECURITY__ENABLE_CORS` | `true` | Enable CORS |
| `allowed_origins` | `DOCLING_MCP_SECURITY__ALLOWED_ORIGINS` | `["*"]` | CORS allowed origins |
| `enable_rate_limiting` | `DOCLING_MCP_SECURITY__ENABLE_RATE_LIMITING` | `false` | Enable rate limiting |
| `max_request_size` | `DOCLING_MCP_SECURITY__MAX_REQUEST_SIZE` | `10485760` | Max request size (bytes) |

## Troubleshooting

### Common Issues

1. **Configuration File Not Found**
   ```bash
   # Create default configuration files
   python docling_mcp_server.py --create-config
   ```

2. **Invalid Configuration**
   ```bash
   # Check validation errors in logs
   python docling_mcp_server.py --environment development 2>&1 | grep -i error
   ```

3. **Environment Variables Not Working**
   ```bash
   # Verify environment variable format
   echo $DOCLING_MCP_SERVER__PORT  # Should use double underscores
   ```

4. **Docker Configuration Issues**
   ```bash
   # Check Docker logs
   docker-compose logs docling-mcp
   
   # Verify volume mounts
   docker-compose config | grep -A5 docling-mcp
   ```

## Testing

Run the configuration test suite:
```bash
cd pmoves_multi_agent_pro_pack
python -m pytest tests/test_configuration.py -v
```

## Support

For configuration-related support:
1. Check the [Configuration Guide](config/CONFIGURATION_GUIDE.md) for detailed documentation
2. Review the configuration schema in `config/config_schema.json`
3. Run the test suite to validate your configuration
4. Check the troubleshooting section above
5. Consult the Docker deployment examples

## Next Steps

1. **Review Your Current Setup**: Identify which hardcoded values you need to externalize
2. **Choose Configuration Method**: Decide between environment variables, YAML files, or a combination
3. **Test in Development**: Use the development configuration to test your setup
4. **Deploy to Production**: Use the production configuration with appropriate security settings
5. **Monitor and Adjust**: Use the configuration system to fine-tune performance and behavior

The new configuration system provides the flexibility needed for modern deployments while maintaining the simplicity and reliability of the original implementation.