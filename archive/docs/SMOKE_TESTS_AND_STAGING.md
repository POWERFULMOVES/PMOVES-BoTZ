# PMOVES Smoke Tests and Staging Guide

This document outlines the smoke testing and staging procedures for PMOVES agent packs.

## Overview

The PMOVES system includes four agent packs with different capabilities:
- **Mini**: Basic portable setup with Tailscale
- **Multi**: Standard multi-agent orchestration
- **Pro**: Advanced with code execution and vision
- **Pro Plus**: Enterprise with automated testing

## Environment Setup

### Consolidated Environment Configuration

All environment variables are now consolidated in `core/example.env`. Copy this file to `.env` in your project root:

```bash
cp core/example.env .env
```

Fill in the required values based on your pack selection:

#### Required for All Packs
- `POSTMAN_API_KEY`: Your Postman API key
- `TS_AUTHKEY`: Tailscale authentication key

#### Mini Pack Only
- `SLACK_BOT_TOKEN`: Slack bot token for notifications
- `DISCORD_WEBHOOK_URL`: Discord webhook for alerts
- `CRUSH_API_KEY`: Crush MCP API key
- `HOSTINGER_API_KEY`: Hostinger deployment API key
- And other infrastructure keys...

#### Pro Pack Only
- `E2B_API_KEY`: E2B sandbox API key
- `VL_PROVIDER`: Vision provider (ollama/openai)
- `OLLAMA_BASE_URL`: Ollama server URL
- `OPENAI_API_KEY`: OpenAI API key (if using OpenAI)

#### Pro Plus Pack Only
- `SLACK_WEBHOOK_URL`: Slack webhook for CI reporting
   - Validates `.env` file exists
   - Checks for required environment variables
   - Verifies variable formatting

2. **Pack Configurations**
   - Validates Docker Compose files for each pack
   - Checks for required configuration files
   - Verifies pack directory structure

3. **API Connectivity**
   - Tests Postman API connection (if key provided)
   - Validates Tailscale configuration
   - Checks external service availability

### Smoke Test Output

```
[14:30:15] INFO: Starting PMOVES smoke tests...
[14:30:15] INFO: Running Environment Configuration tests...
[14:30:15] PASS: Environment file validated
[14:30:16] PASS: Environment Configuration tests PASSED
[14:30:16] INFO: Running Pack Configurations tests...
[14:30:18] PASS: Docker Compose validation passed for pmoves_multi_agent_pack/docker-compose.pmoves-multi.yml
[14:30:19] PASS: Pack Configurations tests PASSED
[14:30:19] INFO: Running API Connectivity tests...
[14:30:20] PASS: Postman API: Connected successfully
[14:30:20] PASS: Tailscale: Auth key configured
[14:30:20] PASS: API Connectivity tests PASSED
[14:30:20] INFO: Smoke tests completed: 3/3 passed
[14:30:20] PASS: All smoke tests PASSED - System ready for deployment
```

## Staging Deployment

Deploy packs to staging environment for verification:

### Deploy Single Pack

```bash
python scripts/stage_deploy.py mini
python scripts/stage_deploy.py multi
python scripts/stage_deploy.py pro
python scripts/stage_deploy.py pro_plus
```

### Deploy All Packs

```bash
python scripts/stage_deploy.py
```

### Deployment Process

1. **Pre-deployment Checks**
   - Runs full smoke test suite
   - Validates environment configuration
   - Aborts if critical issues found

2. **Service Deployment**
   - Stops existing containers
   - Starts services with staging configuration
   - Waits for services to initialize

3. **Health Verification**
   - Checks service health endpoints
   - Validates Docker container status
   - Reports any failed health checks

4. **Post-deployment Testing**
   - Verifies all services are running
   - Checks container logs for errors
   - Reports deployment status

### Deployment Output Example

```
[14:35:00] INFO: Running pre-deployment checks...
[14:35:05] PASS: Pre-deployment checks passed
[14:35:05] INFO: Deploying multi pack...
[14:35:05] INFO: Stopping existing services...
[14:35:08] INFO: Starting services...
[14:35:15] INFO: Waiting for services to be ready...
[14:35:25] INFO: All health checks passed
[14:35:25] INFO: Running post-deployment tests...
[14:35:28] PASS: Post-deployment tests completed
[14:35:28] PASS: multi pack deployed successfully

✅ Staging deployment completed successfully!
Run 'python scripts/smoke_tests.py' to verify functionality
```

## Verification Procedures

### Manual Verification Steps

After automated deployment, perform these manual checks:

#### 1. Service Accessibility
```bash
# Check running containers
docker ps

# Check service logs
docker-compose -f pmoves_multi_agent_pack/docker-compose.pmoves-multi.yml logs

# Test health endpoints
curl http://localhost:3020/health
curl http://localhost:3021/health
```

#### 2. MCP Server Testing
```bash
# Test MCP server connections
# Use Kilo Code or MCP client to connect to running servers
```

#### 3. Integration Testing
- Test Postman collection execution
- Verify Docling document processing
- Check workflow integrations (N8N, etc.)
- Validate notification channels

#### 4. Performance Validation
- Monitor resource usage
- Check response times
- Verify concurrent request handling

### Troubleshooting

#### Common Issues

**Environment Variables Missing**
```
Solution: Copy core/example.env to .env and fill in required values
```

**Docker Compose Validation Failed**
```
Solution: Check Docker and Docker Compose installation
Run: docker --version && docker-compose --version
```

**API Connectivity Failed**
```
Solution: Verify API keys in .env file
Test manually: curl -H "X-API-Key: YOUR_KEY" https://api.postman.com/me
```

**Health Checks Failing**
```
Solution: Check container logs for errors
Run: docker-compose logs <service_name>
```

#### Logs and Debugging

```bash
# View all logs
docker-compose -f <compose_file> logs -f

# View specific service logs
docker-compose -f <compose_file> logs <service_name>

# Restart failed services
docker-compose -f <compose_file> restart <service_name>
```

## CI/CD Integration

For automated deployments, integrate with your CI pipeline:

```yaml
# .github/workflows/staging.yml
name: Staging Deployment
on:
  push:
    branches: [staging]

jobs:
  test-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.8'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run smoke tests
        run: python scripts/smoke_tests.py
      - name: Deploy to staging
        run: python scripts/stage_deploy.py
```

## Support

For issues or questions:
1. Check this documentation
2. Review smoke test output for specific errors
3. Check Docker and service logs
4. Verify environment configuration
5. Test API keys manually

The automated scripts provide detailed logging to help diagnose issues quickly.