# Troubleshooting Scripts and Utilities

This document contains the complete troubleshooting scripts and utilities referenced in the main troubleshooting guide. These scripts are designed to help diagnose, monitor, and resolve issues with the docling-mcp service.

## Table of Contents

1. [Diagnostic Script](#diagnostic-script)
2. [Health Check Script](#health-check-script)
3. [Performance Monitoring Script](#performance-monitoring-script)
4. [Configuration Validation Script](#configuration-validation-script)
5. [Log Analysis Script](#log-analysis-script)
6. [Service Recovery Script](#service-recovery-script)

## Diagnostic Script

### File: `docling_mcp_diagnostics.sh`

```bash
#!/bin/bash
# docling_mcp_diagnostics.sh - Comprehensive diagnostic script

set -e

echo "=== Docling MCP Service Diagnostics ==="
echo "Date: $(date)"
echo "System: $(uname -a)"
echo "Docker Version: $(docker --version)"
echo ""

echo "=== Service Status ==="
docker compose -f docker-compose.mcp-pro.yml ps
echo ""

echo "=== Recent Logs (last 50 lines) ==="
for service in docling-mcp mcp-gateway; do
    echo "--- $service ---"
    docker logs pmoves_multi_agent_pro_pack-${service}-1 --tail 50 | grep -i error || echo "No recent errors"
done
echo ""

echo "=== Network Connectivity ==="
echo "Testing docling-mcp endpoint:"
curl -v -H "Accept: text/event-stream" http://localhost:3020/mcp 2>&1 | head -20
echo ""
echo "Testing mcp-gateway endpoint:"
curl -v http://localhost:2091/health 2>&1 | head -20
echo ""

echo "=== Container Resource Usage ==="
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
echo ""

echo "=== Configuration Check ==="
echo "Environment variables:"
docker exec -it pmoves_multi_agent_pro_pack-docling-mcp-1 env | grep DOCLING_MCP | sort
echo ""

echo "=== Volume Mounts ==="
docker inspect pmoves_multi_agent_pro_pack-docling-mcp-1 | grep -A 20 Mounts
echo ""

echo "=== Health Check Status ==="
curl -f http://localhost:3020/health > /dev/null 2>&1 && echo "Docling-MCP: OK" || echo "Docling-MCP: FAILED"
curl -f http://localhost:2091/health > /dev/null 2>&1 && echo "MCP-Gateway: OK" || echo "MCP-Gateway: FAILED"
echo ""

echo "=== Port Availability ==="
netstat -an | grep -E "3020|2091" || echo "No ports found"
echo ""

echo "=== Disk Usage ==="
df -h | grep -E "/$|/data"
echo ""

echo "=== Memory Usage ==="
free -h
echo ""

echo "=== Docker System Info ==="
docker system df
echo ""

echo "=== Diagnostics Complete ==="
```

### Usage

```bash
# Make script executable
chmod +x docling_mcp_diagnostics.sh

# Run diagnostics
./docling_mcp_diagnostics.sh

# Save output to file
./docling_mcp_diagnostics.sh > diagnostics_$(date +%Y%m%d_%H%M%S).log
```

## Health Check Script

### File: `health_check.sh`

```bash
#!/bin/bash
# health_check.sh - Service health monitoring script

set -e

SERVICES=("docling-mcp" "mcp-gateway")
ENDPOINTS=("http://localhost:3020/health" "http://localhost:2091/health")
LOG_FILE="/var/log/docling-mcp-health.log"

# Create log file if it doesn't exist
touch "$LOG_FILE"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to check service health
check_service() {
    local service=$1
    local endpoint=$2
    
    if curl -f "$endpoint" > /dev/null 2>&1; then
        log_message "$service: HEALTHY"
        return 0
    else
        log_message "$service: UNHEALTHY"
        return 1
    fi
}

# Check all services
for i in "${!SERVICES[@]}"; do
    service="${SERVICES[$i]}"
    endpoint="${ENDPOINTS[$i]}"
    
    if ! check_service "$service" "$endpoint"; then
        log_message "Restarting $service..."
        docker compose -f docker-compose.mcp-pro.yml restart "$service"
        
        # Wait for service to start
        sleep 30
        
        # Check again
        if check_service "$service" "$endpoint"; then
            log_message "$service: RECOVERED"
        else
            log_message "$service: FAILED TO RECOVER - Manual intervention required"
        fi
    fi
done
```

### Usage

```bash
# Make script executable
chmod +x health_check.sh

# Run health check
./health_check.sh

# Set up cron job for automated monitoring
echo "*/5 * * * * /path/to/health_check.sh" | crontab -
```

## Performance Monitoring Script

### File: `performance_monitor.sh`

```bash
#!/bin/bash
# performance_monitor.sh - Performance monitoring script

set -e

METRICS_FILE="/var/log/docling-mcp-metrics.log"
ALERT_THRESHOLD_CPU=80
ALERT_THRESHOLD_MEMORY=80
ALERT_THRESHOLD_RESPONSE_TIME=2000

# Create metrics file if it doesn't exist
touch "$METRICS_FILE"

# Function to log metrics
log_metrics() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local cpu_usage=$(docker stats --no-stream --format "{{.CPUPerc}}" pmoves_multi_agent_pro_pack-docling-mcp-1 | sed 's/%//')
    local memory_usage=$(docker stats --no-stream --format "{{.MemPerc}}" pmoves_multi_agent_pro_pack-docling-mcp-1 | sed 's/%//')
    local response_time=$(curl -o /dev/null -s -w "%{time_total}" http://localhost:3020/health)
    
    echo "$timestamp,$cpu_usage,$memory_usage,$response_time" >> "$METRICS_FILE"
    
    # Check thresholds
    if (( $(echo "$cpu_usage > $ALERT_THRESHOLD_CPU" | bc -l) )); then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - ALERT: High CPU usage: $cpu_usage%" >> "$METRICS_FILE"
    fi
    
    if (( $(echo "$memory_usage > $ALERT_THRESHOLD_MEMORY" | bc -l) )); then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - ALERT: High memory usage: $memory_usage%" >> "$METRICS_FILE"
    fi
    
    if (( $(echo "$response_time > $ALERT_THRESHOLD_RESPONSE_TIME" | bc -l) )); then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - ALERT: High response time: ${response_time}ms" >> "$METRICS_FILE"
    fi
}

# Monitor continuously
while true; do
    log_metrics
    sleep 60  # Collect metrics every minute
done
```

### Usage

```bash
# Make script executable
chmod +x performance_monitor.sh

# Run performance monitoring (in background)
./performance_monitor.sh &

# Stop monitoring
pkill -f performance_monitor.sh
```

## Configuration Validation Script

### File: `config_validator.sh`

```bash
#!/bin/bash
# config_validator.sh - Configuration validation script

set -e

CONFIG_FILE="${1:-/srv/config/default.yaml}"
ERRORS=0

# Function to report errors
report_error() {
    echo "ERROR: $1"
    ERRORS=$((ERRORS + 1))
}

# Function to report warnings
report_warning() {
    echo "WARNING: $1"
}

echo "=== Configuration Validation ==="
echo "Checking configuration file: $CONFIG_FILE"
echo ""

# Check if configuration file exists
if [ ! -f "$CONFIG_FILE" ]; then
    report_error "Configuration file not found: $CONFIG_FILE"
    exit 1
fi

# Validate YAML syntax
if ! python -c "import yaml; yaml.safe_load(open('$CONFIG_FILE'))" 2>/dev/null; then
    report_error "Invalid YAML syntax in configuration file"
fi

# Check required sections
if ! grep -q "server:" "$CONFIG_FILE"; then
    report_error "Missing 'server' section in configuration"
fi

if ! grep -q "logging:" "$CONFIG_FILE"; then
    report_error "Missing 'logging' section in configuration"
fi

# Validate server configuration
if grep -q "port:" "$CONFIG_FILE"; then
    port=$(grep "port:" "$CONFIG_FILE" | awk '{print $2}')
    if ! [[ "$port" =~ ^[0-9]+$ ]] || [ "$port" -lt 1 ] || [ "$port" -gt 65535 ]; then
        report_error "Invalid port number: $port (must be 1-65535)"
    fi
fi

# Validate logging configuration
if grep -q "level:" "$CONFIG_FILE"; then
    level=$(grep "level:" "$CONFIG_FILE" | awk '{print $2}' | tr -d '"')
    case "$level" in
        DEBUG|INFO|WARNING|ERROR)
            # Valid log level
            ;;
        *)
            report_error "Invalid log level: $level (must be DEBUG, INFO, WARNING, or ERROR)"
            ;;
    esac
fi

# Check security settings
if grep -q "enable_cors: true" "$CONFIG_FILE"; then
    if grep -q "allowed_origins:" "$CONFIG_FILE"; then
        origins=$(grep -A 5 "allowed_origins:" "$CONFIG_FILE" | grep -E '^\s*-' | wc -l)
        if [ "$origins" -eq 0 ]; then
            report_warning "CORS enabled but no allowed origins specified"
        fi
    fi
fi

# Check performance settings
if grep -q "tool_timeout:" "$CONFIG_FILE"; then
    timeout=$(grep "tool_timeout:" "$CONFIG_FILE" | awk '{print $2}')
    if ! [[ "$timeout" =~ ^[0-9]+\.?[0-9]*$ ]] || [ "$timeout" -le 0 ]; then
        report_error "Invalid tool timeout: $timeout (must be positive number)"
    fi
fi

# Report results
echo ""
if [ "$ERRORS" -eq 0 ]; then
    echo "Configuration validation PASSED"
    exit 0
else
    echo "Configuration validation FAILED with $ERRORS error(s)"
    exit 1
fi
```

### Usage

```bash
# Make script executable
chmod +x config_validator.sh

# Validate default configuration
./config_validator.sh

# Validate custom configuration
./config_validator.sh /path/to/custom/config.yaml
```

## Log Analysis Script

### File: `log_analyzer.sh`

```bash
#!/bin/bash
# log_analyzer.sh - Log analysis script

set -e

LOG_FILE="${1:-/var/log/docling-mcp.log}"
ANALYSIS_TYPE="${2:-errors}"

# Function to analyze errors
analyze_errors() {
    echo "=== Error Analysis ==="
    echo "Analyzing errors in $LOG_FILE..."
    
    # Count errors by type
    echo "Error counts:"
    grep -i "error\|exception\|failed" "$LOG_FILE" | \
        awk '{print $NF}' | sort | uniq -c | sort -nr
    
    # Recent errors
    echo ""
    echo "Recent errors (last 10):"
    grep -i "error\|exception\|failed" "$LOG_FILE" | tail -10
    
    # Error patterns by hour
    echo ""
    echo "Errors by hour:"
    grep -i "error\|exception\|failed" "$LOG_FILE" | \
        awk '{print $1 " " $2}' | \
        awk '{gsub(/:/, "", $2); print $2}' | \
        sort | uniq -c
}

# Function to analyze performance
analyze_performance() {
    echo "=== Performance Analysis ==="
    echo "Analyzing performance in $LOG_FILE..."
    
    # Response times
    echo "Response time statistics:"
    grep "response_time" "$LOG_FILE" | \
        awk '{print $NF}' | \
        awk '{sum+=$1; count++} END {print "Average:", sum/count, "Count:", count}'
    
    # Tool execution times
    echo ""
    echo "Tool execution times:"
    grep "tool_execution" "$LOG_FILE" | \
        awk '{print $NF}' | \
        sort -n | \
        awk 'BEGIN{min=999999; max=0} {if($1<min) min=$1; if($1>max) max=$1; sum+=$1; count++} END {print "Min:", min, "Max:", max, "Avg:", sum/count}'
    
    # Connection patterns
    echo ""
    echo "Connection patterns:"
    grep "connection" "$LOG_FILE" | \
        awk '{print $1 " " $2}' | \
        awk '{gsub(/:/, "", $2); print $2}' | \
        sort | uniq -c | sort -nr | head -10
}

# Function to analyze usage
analyze_usage() {
    echo "=== Usage Analysis ==="
    echo "Analyzing usage patterns in $LOG_FILE..."
    
    # Tool usage
    echo "Tool usage:"
    grep "tool_call" "$LOG_FILE" | \
        awk '{for(i=1;i<=NF;i++) if($i ~ /tool=/) print $i}' | \
        sed 's/.*tool=//' | \
        sort | uniq -c | sort -nr
    
    # Client connections
    echo ""
    echo "Client connections:"
    grep "connection from" "$LOG_FILE" | \
        awk '{print $NF}' | \
        sort | uniq -c | sort -nr | head -10
    
    # Request patterns
    echo ""
    echo "Request patterns by hour:"
    grep "request" "$LOG_FILE" | \
        awk '{print $1 " " $2}' | \
        awk '{gsub(/:/, "", $2); print $2}' | \
        sort | uniq -c | sort -nr
}

# Main execution
case "$ANALYSIS_TYPE" in
    errors)
        analyze_errors
        ;;
    performance)
        analyze_performance
        ;;
    usage)
        analyze_usage
        ;;
    all)
        analyze_errors
        echo ""
        analyze_performance
        echo ""
        analyze_usage
        ;;
    *)
        echo "Usage: $0 <log_file> <analysis_type>"
        echo "Analysis types: errors, performance, usage, all"
        exit 1
        ;;
esac
```

### Usage

```bash
# Make script executable
chmod +x log_analyzer.sh

# Analyze errors
./log_analyzer.sh /var/log/docling-mcp.log errors

# Analyze performance
./log_analyzer.sh /var/log/docling-mcp.log performance

# Analyze usage patterns
./log_analyzer.sh /var/log/docling-mcp.log usage

# Analyze everything
./log_analyzer.sh /var/log/docling-mcp.log all
```

## Service Recovery Script

### File: `service_recovery.sh`

```bash
#!/bin/bash
# service_recovery.sh - Service recovery script

set -e

SERVICE="${1:-docling-mcp}"
RECOVERY_TYPE="${2:-restart}"
BACKUP_DIR="/backup/docling-mcp"

# Function to backup service
backup_service() {
    local service=$1
    local backup_dir="$BACKUP_DIR/$(date +%Y%m%d_%H%M%S)"
    
    echo "Creating backup of $service..."
    mkdir -p "$backup_dir"
    
    # Backup configuration
    docker exec -it pmoves_multi_agent_pro_pack-${service}-1 cat /srv/config/default.yaml > "$backup_dir/config.yaml"
    
    # Backup logs
    docker logs pmoves_multi_agent_pro_pack-${service}-1 > "$backup_dir/service.log"
    
    # Backup data
    if [ -d "./data/$service" ]; then
        cp -r "./data/$service" "$backup_dir/"
    fi
    
    echo "Backup created at $backup_dir"
}

# Function to restart service
restart_service() {
    local service=$1
    
    echo "Restarting $service..."
    docker compose -f docker-compose.mcp-pro.yml restart "$service"
    
    # Wait for service to be healthy
    echo "Waiting for $service to be healthy..."
    for i in {1..30}; do
        if docker compose -f docker-compose.mcp-pro.yml ps "$service" | grep -q "healthy"; then
            echo "$service is healthy"
            return 0
        fi
        sleep 2
    done
    
    echo "$service failed to become healthy"
    return 1
}

# Function to rebuild service
rebuild_service() {
    local service=$1
    
    echo "Rebuilding $service..."
    docker compose -f docker-compose.mcp-pro.yml stop "$service"
    docker compose -f docker-compose.mcp-pro.yml rm "$service"
    docker compose -f docker-compose.mcp-pro.yml build "$service"
    docker compose -f docker-compose.mcp-pro.yml up -d "$service"
    
    # Wait for service to be healthy
    echo "Waiting for $service to be healthy..."
    for i in {1..60}; do
        if docker compose -f docker-compose.mcp-pro.yml ps "$service" | grep -q "healthy"; then
            echo "$service is healthy"
            return 0
        fi
        sleep 2
    done
    
    echo "$service failed to become healthy"
    return 1
}

# Function to reset service
reset_service() {
    local service=$1
    
    echo "Resetting $service..."
    
    # Create backup
    backup_service "$service"
    
    # Stop and remove service
    docker compose -f docker-compose.mcp-pro.yml stop "$service"
    docker compose -f docker-compose.mcp-pro.yml rm "$service"
    
    # Clean up data (optional)
    read -p "Clean up service data? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Cleaning up data..."
        rm -rf "./data/$service"
    fi
    
    # Rebuild and start
    rebuild_service "$service"
}

# Main execution
echo "=== Service Recovery ==="
echo "Service: $SERVICE"
echo "Recovery type: $RECOVERY_TYPE"
echo ""

case "$RECOVERY_TYPE" in
    restart)
        restart_service "$SERVICE"
        ;;
    rebuild)
        rebuild_service "$SERVICE"
        ;;
    reset)
        reset_service "$SERVICE"
        ;;
    backup)
        backup_service "$SERVICE"
        ;;
    *)
        echo "Usage: $0 <service> <recovery_type>"
        echo "Services: docling-mcp, mcp-gateway"
        echo "Recovery types: restart, rebuild, reset, backup"
        exit 1
        ;;
esac

echo "Recovery completed"
```

### Usage

```bash
# Make script executable
chmod +x service_recovery.sh

# Restart service
./service_recovery.sh docling-mcp restart

# Rebuild service
./service_recovery.sh docling-mcp rebuild

# Reset service (with backup)
./service_recovery.sh docling-mcp reset

# Create backup only
./service_recovery.sh docling-mcp backup
```

## Installation and Setup

### Prerequisites

1. **Docker and Docker Compose**:
   ```bash
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   
   # Install Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

2. **Required Tools**:
   ```bash
   # Install required tools
   sudo apt-get update
   sudo apt-get install -y curl bc jq
   
   # On macOS
   brew install curl bc jq
   ```

### Script Installation

1. **Download Scripts**:
   ```bash
   # Create scripts directory
   mkdir -p ~/docling-mcp-scripts
   cd ~/docling-mcp-scripts
   
   # Download scripts (copy from documentation)
   # Each script should be saved to its respective file
   ```

2. **Make Scripts Executable**:
   ```bash
   # Make all scripts executable
   chmod +x *.sh
   ```

3. **Set Up Cron Jobs**:
   ```bash
   # Edit crontab
   crontab -e
   
   # Add monitoring jobs
   */5 * * * * /home/user/docling-mcp-scripts/health_check.sh
   0 * * * * /home/user/docling-mcp-scripts/performance_monitor.sh
   ```

4. **Configure Log Rotation**:
   ```bash
   # Create logrotate configuration
   sudo tee /etc/logrotate.d/docling-mcp << EOF
   /var/log/docling-mcp*.log {
       daily
       rotate 7
       compress
       delaycompress
       missingok
       notifempty
       create 644 root root
   }
   EOF
   ```

## Integration with Existing Documentation

These scripts are referenced in the main troubleshooting guide ([`TROUBLESHOOTING.md`](TROUBLESHOOTING.md)) and provide automated solutions for common issues:

- **Diagnostic Script**: Used for comprehensive system analysis
- **Health Check Script**: Used for automated service monitoring
- **Performance Monitoring Script**: Used for performance tracking and alerting
- **Configuration Validation Script**: Used for configuration verification
- **Log Analysis Script**: Used for log pattern analysis
- **Service Recovery Script**: Used for automated service recovery

Each script includes detailed usage instructions and can be customized for specific deployment environments.