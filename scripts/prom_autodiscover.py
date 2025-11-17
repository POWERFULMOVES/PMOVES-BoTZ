#!/usr/bin/env python3
import json, os, subprocess, sys, yaml, re

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
FILE_SD = os.path.join(BASE_DIR, 'features', 'metrics', 'file_sd', 'blackbox_targets.yml')
CODEX_DIR = os.path.join(BASE_DIR, 'config', 'codex')
LOCAL_MCP_JSON = os.path.join(CODEX_DIR, 'local_mcp.json')
PROM_YML = os.path.join(BASE_DIR, 'features', 'metrics', 'prometheus.yml')

def sh(cmd):
    # Capture stderr so failing docker inspect calls don't spam the console.
    p = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if p.returncode != 0:
        raise subprocess.CalledProcessError(p.returncode, cmd, output=p.stdout, stderr=p.stderr)
    return p.stdout

def container_exists(name_substr: str) -> bool:
    try:
        out = sh("docker ps --format '{{.Names}}'")
        # Normalize CRLF if present on Windows
        lines = out.replace('\r','').splitlines()
        return any(name_substr in line for line in lines)
    except Exception:
        return False

def load_static_blackbox_targets():
    """Load static blackbox targets from Prometheus config to avoid duplicates."""
    skip = set()
    try:
        with open(PROM_YML, 'r') as f:
            p = yaml.safe_load(f)
        scs = p.get('scrape_configs', []) or []
        for sc in scs:
            if sc.get('job_name') == 'blackbox':
                for cfg in sc.get('static_configs', []) or []:
                    for t in cfg.get('targets', []) or []:
                        skip.add(str(t))
    except Exception:
        pass
    return skip


def build_targets():
    targets = []
    # Label-based autodiscovery only. Skip anything already present in Prometheus static_configs.
    # We include any container exposing 'pmoves.health' on any network name containing 'pmoves'.
    skip_urls = load_static_blackbox_targets()
    seen = set()  # (service, url)
    try:
        raw = sh("docker ps --format '{{.Names}}'")
        names = raw.replace('\r','').splitlines()
        for name in names:
            # Inspect labels and networks
            try:
                insp = sh(f"docker inspect {name}")
                info = json.loads(insp)[0]
                labels = info.get('Config', {}).get('Labels', {}) or {}
                networks = info.get('NetworkSettings', {}).get('Networks', {}) or {}
                if not any('pmoves' in net.lower() for net in networks.keys()):
                    continue
                health = labels.get('pmoves.health') or labels.get('pmoves_health')
                service = labels.get('pmoves.service') or name
                if health:
                    # Skip if covered by static blackbox config
                    if str(health) in skip_urls:
                        continue
                    key = (service, health)
                    if key in seen:
                        continue
                    seen.add(key)
                    targets.append({'targets': [health], 'labels': {'service': service}})
            except Exception:
                continue
    except Exception:
        pass

    return targets

def main():
    os.makedirs(os.path.dirname(FILE_SD), exist_ok=True)
    data = build_targets()
    with open(FILE_SD, 'w') as f:
        yaml.safe_dump(data, f, sort_keys=False)
    print(f"Wrote {FILE_SD} with {len(data)} target blocks")

    prom_port = os.environ.get('PROMETHEUS_PORT', '9090')
    try:
        sh(f"curl -fsS -X POST http://localhost:{prom_port}/-/reload >/dev/null")
        print("Prometheus reloaded")
    except Exception:
        print("Warn: could not reload Prometheus; it will pick up on restart.")

    # Generate dynamic Codex/Kilo MCP config mapping to gateway and direct endpoints (if host ports are mapped)
    try:
        os.makedirs(CODEX_DIR, exist_ok=True)
        ns = os.environ.get('PMZ_NAMESPACE', os.environ.get('COMPOSE_PROJECT_NAME', 'pmoves-botz'))
        def host_port(svc, cport):
            name = f"{ns}-{svc}-1"
            try:
                insp = json.loads(sh(f"docker inspect {name}"))[0]
                ports = insp.get('NetworkSettings', {}).get('Ports', {}) or {}
                key = f"{cport}/tcp"
                arr = ports.get(key)
                if arr and len(arr)>0 and arr[0].get('HostPort'):
                    return arr[0]['HostPort']
            except Exception:
                return None
            return None

        cfg = { 'mcpServers': {} }
        # Gateway local
        gw_port = os.environ.get('GATEWAY_PORT') or host_port('mcp-gateway', '8000') or '2091'
        cfg['mcpServers']['pmoves-gateway-local'] = { 'transport':'http', 'url': f"http://localhost:{gw_port}" }
        # Cipher direct (if mapped)
        cipher_api = os.environ.get('CIPHER_API_PORT') or host_port('cipher-memory','3011')
        if cipher_api:
            cfg['mcpServers']['cipher-direct'] = { 'transport':'http', 'url': f"http://localhost:{cipher_api}" }
        # Crush direct (if mapped)
        crush_port = os.environ.get('CRUSH_PORT') or host_port('crush-shim','7069')
        if crush_port:
            cfg['mcpServers']['crush-direct'] = { 'transport':'http', 'url': f"http://localhost:{crush_port}" }

        with open(LOCAL_MCP_JSON, 'w') as f:
            json.dump(cfg, f, indent=2)
        print(f"Wrote {LOCAL_MCP_JSON}")
    except Exception as e:
        print(f"Warn: could not write local MCP config: {e}")

if __name__ == '__main__':
    main()
