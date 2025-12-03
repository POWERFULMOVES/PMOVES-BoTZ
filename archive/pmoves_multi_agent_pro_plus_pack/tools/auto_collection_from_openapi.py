#!/usr/bin/env python3
"""Generate a Postman collection from an OpenAPI (JSON or YAML).
- If POSTMAN_API_KEY and (optionally) POSTMAN_WORKSPACE_ID are set, uploads to Postman via REST API.
- Otherwise writes `out.collection.json` locally.
"""
import os, sys, json, re
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

POSTMAN_API = os.environ.get("POSTMAN_API_BASE_URL","https://api.postman.com").rstrip("/")

def load_openapi(path: Path):
    data = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml",".yml"):
        if yaml is None:
            raise SystemExit("PyYAML not installed. pip install pyyaml")
        return yaml.safe_load(data)
    try:
        return json.loads(data)
    except Exception as e:
        raise SystemExit(f"OpenAPI must be JSON or YAML. {e}")

def make_request_items(spec: dict):
    # Build Postman items from 'paths'
    items = []
    paths = spec.get("paths", {})
    servers = spec.get("servers", [])
    base_url = ""
    if servers and isinstance(servers, list) and servers[0].get("url"):
        base_url = servers[0]["url"].rstrip("/")
    for path, ops in paths.items():
        for method, op in ops.items():
            if method.upper() not in ("GET","POST","PUT","DELETE","PATCH","HEAD","OPTIONS","TRACE"):
                continue
            name = op.get("summary") or f"{method.upper()} {path}"
            url = f"{base_url}{path}"
            req = {
                "name": name,
                "request": {
                    "method": method.upper(),
                    "header": [],
                    "url": {"raw": url, "host": [url]}
                }
            }
            items.append(req)
    return items

def make_collection(spec: dict, name: str):
    return {
        "info": {"name": name, "_postman_id": "", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
        "item": make_request_items(spec)
    }

def upload_collection(coll: dict, name: str, workspace_id: str | None, api_key: str):
    import requests
    url = f"{POSTMAN_API}/collections"
    params = {}
    if workspace_id:
        params["workspace"] = workspace_id
    headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}
    r = requests.post(url, params=params, headers=headers, json={"collection": coll}, timeout=60)
    if not r.ok:
        raise SystemExit(f"Postman API error: {r.status_code} {r.text}")
    data = r.json()
    cid = data.get("collection",{}).get("uid") or data.get("uid")
    return cid, data

def main():
    if len(sys.argv) < 3:
        print("Usage: auto_collection_from_openapi.py <openapi.(json|yaml)> <collection-name> [--no-upload]")
        sys.exit(1)
    openapi_path = Path(sys.argv[1])
    coll_name = sys.argv[2]
    no_upload = ("--no-upload" in sys.argv)
    spec = load_openapi(openapi_path)
    coll = make_collection(spec, coll_name)
    if no_upload or not os.environ.get("POSTMAN_API_KEY"):
        out = Path("out.collection.json")
        out.write_text(json.dumps({"collection": coll}, indent=2), encoding="utf-8")
        print(f"Wrote {out}")
        return
    key = os.environ["POSTMAN_API_KEY"]
    ws = os.environ.get("POSTMAN_WORKSPACE_ID")
    cid, data = upload_collection(coll, coll_name, ws, key)
    print(json.dumps({"uploaded": True, "collection_uid": cid, "response": data}, indent=2))

if __name__ == "__main__":
    main()