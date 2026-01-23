# Glancer System Status

Get system and network information using Glances (Pmoves-Glancer).

## Arguments

- `$ARGUMENTS` - Optional: specific metric (cpu, mem, disk, network, sensors, all)

## Instructions

1. Query Glances REST API for system metrics
2. Format key metrics for display
3. Highlight any concerning values (high CPU, low memory, etc.)

```bash
# Get all system stats
curl -s http://localhost:9105/api/4/all | jq '.'

# Get specific metrics
curl -s http://localhost:9105/api/4/cpu | jq '.'       # CPU usage
curl -s http://localhost:9105/api/4/mem | jq '.'       # Memory usage
curl -s http://localhost:9105/api/4/fs | jq '.'        # Filesystem/disk
curl -s http://localhost:9105/api/4/network | jq '.'   # Network interfaces
curl -s http://localhost:9105/api/4/sensors | jq '.'   # Temperature sensors
curl -s http://localhost:9105/api/4/gpu | jq '.'       # GPU info (if available)
```

## Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/4/all` | All system metrics |
| `/api/4/cpu` | CPU usage and stats |
| `/api/4/mem` | Memory usage |
| `/api/4/swap` | Swap usage |
| `/api/4/load` | System load |
| `/api/4/fs` | Filesystem usage |
| `/api/4/diskio` | Disk I/O stats |
| `/api/4/network` | Network interfaces |
| `/api/4/sensors` | Temperature sensors |
| `/api/4/gpu` | GPU metrics |
| `/api/4/docker` | Docker container stats |
| `/api/4/processlist` | Running processes |

## Thresholds (Warning Levels)

- CPU: > 80% warning, > 95% critical
- Memory: > 80% warning, > 95% critical
- Disk: > 80% warning, > 95% critical
- Temperature: > 70°C warning, > 85°C critical

Report:
- CPU usage (per-core if available)
- Memory used/total
- Disk usage by mount
- Network throughput
- GPU utilization (5090)
- Any warnings/alerts
