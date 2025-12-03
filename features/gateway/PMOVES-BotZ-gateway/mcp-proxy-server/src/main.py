from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount
from prometheus_client import CollectorRegistry, Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
import os, sys, shlex, yaml

MAX_ARGS = 64
MAX_ARG_LEN = 512
MAX_SERVERS = 64

def bad(msg: str):
    print(f"[gateway] {msg}", file=sys.stderr)
    sys.exit(1)

def safe(arg: str) -> bool:
    return (
        isinstance(arg, str)
        and 0 < len(arg) <= MAX_ARG_LEN
        and "\x00" not in arg
        and "\n" not in arg
        and "\r" not in arg
    )

def load_catalog_config() -> dict | None:
    path = os.environ.get("MCP_CATALOG_PATH")
    if not path:
        return None
    if not os.path.exists(path):
        bad(f"MCP_CATALOG_PATH not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    servers = data.get("mcpServers") or data.get("mcp_servers")
    if not isinstance(servers, dict) or not servers:
        bad("Catalog missing 'mcpServers' mapping")
    if len(servers) > MAX_SERVERS:
        bad("Too many servers in catalog")

    normalized: dict[str, dict] = {}
    for name, cfg in servers.items():
        if not isinstance(cfg, dict):
            bad(f"Invalid server config for {name}")
        ncfg = dict(cfg)
        # HTTP upstream
        if "url" in ncfg:
            url = str(ncfg["url"]).strip()
            # Allow internal hostnames; do not enforce TLD validation
            if not (url.startswith("http://") or url.startswith("https://")):
                bad(f"Invalid URL for {name}")
            ncfg.setdefault("transport", "http")
            for k in ("command", "args", "type"):
                ncfg.pop(k, None)
        else:
            # STDIO upstream
            cmd = ncfg.get("command")
            args = ncfg.get("args", [])
            if not cmd or not safe(str(cmd)):
                bad(f"Unsafe or missing command for {name}")
            if not isinstance(args, (list, tuple)):
                bad(f"Args must be list for {name}")
            if len(args) > MAX_ARGS:
                bad(f"Too many args for {name}")
            if any(not safe(str(a)) for a in args):
                bad(f"Unsafe arg in {name}")
            ncfg["type"] = "stdio"
            env = dict(os.environ)
            if isinstance(ncfg.get("env"), dict):
                env.update({str(k): str(v) for k, v in ncfg["env"].items()})
            ncfg["env"] = env
        normalized[name] = ncfg

    return {"mcpServers": normalized}

def build_config() -> dict:
    # Prefer catalog if provided
    cat = load_catalog_config()
    if cat:
        return cat

    proxy_url = os.environ.get("MCP_PROXY_URL")
    if proxy_url:
        if not (proxy_url.startswith("http://") or proxy_url.startswith("https://")):
            bad("Invalid MCP_PROXY_URL: must be http(s)")
        return {"mcpServers": {"default": {"url": proxy_url, "transport": "http"}}}

    cmd = os.environ.get("MCP_COMMAND")
    if not cmd:
        bad("Must set MCP_CATALOG_PATH, MCP_PROXY_URL, or MCP_COMMAND")
    raw_args = os.environ.get("MCP_ARGS", "")
    args = shlex.split(raw_args) if raw_args else []
    if not safe(cmd):
        bad("Unsafe command")
    if len(args) > MAX_ARGS:
        bad("Too many args")
    for a in args:
        if not safe(a):
            bad(f"Unsafe arg: {a!r}")
    return {
        "mcpServers": {
            "default": {
                "type": "stdio",
                "command": cmd,
                "args": args,
                "env": dict(os.environ),
            }
        }
    }

# Build proxy and wrap with Starlette app to provide /health
config = build_config()
proxy = FastMCP.as_proxy(config, name="PMOVES BotZ Gateway")
mcp_app = proxy.http_app()

# Basic metrics registry for the proxy
REGISTRY = CollectorRegistry()
MCP_PROXY_UP = Gauge('mcp_proxy_up', 'Gateway up status', registry=REGISTRY)
HTTP_REQUESTS_TOTAL = Counter('http_requests_total', 'HTTP Requests', ['path','method','status'], registry=REGISTRY)
MCP_PROXY_UP.set(1)

async def health(_request):
    HTTP_REQUESTS_TOTAL.labels(path='/health', method='GET', status='200').inc()
    return JSONResponse({"status": "healthy", "service": "PMOVES BotZ Gateway"})

async def metrics(_request):
    from starlette.responses import Response
    data = generate_latest(REGISTRY)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

app = Starlette(routes=[
    Route("/health", endpoint=health),
    Route("/ready", endpoint=health),
    Route("/metrics", endpoint=metrics),
    Route("/gateway/metrics", endpoint=metrics),
    Mount("/", app=mcp_app)
])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
