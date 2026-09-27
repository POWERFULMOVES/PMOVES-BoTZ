#!/usr/bin/env python3
"""Test GitHub App token minting."""

import os
import time
import jwt
import requests

# Load environment variables
env_file = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "pmoves", "env.tier-agent"
)

# Read the env file and parse variables
creds = {}
with open(env_file) as f:
    current_key = None
    pem_lines = []
    in_pem = False

    for line in f:
        line = line.rstrip("\n")
        if line.startswith("GH_APP_SEC="):
            pem_lines.append(line.split("=", 1)[1].strip())
            in_pem = True
        elif in_pem:
            # Check if this is still part of the PEM or a new variable
            if line.startswith("-----END") or line.startswith("HOSTINGER_"):
                pem_lines.append(line)
                in_pem = False
                creds["GH_APP_SEC"] = "\n".join(pem_lines)
            else:
                pem_lines.append(line)
        elif "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            if key.startswith("GH_APP_"):
                creds[key] = value

app_id = creds["GH_APP_ID"]
pem = creds["GH_APP_SEC"]
install_id = creds["GH_APP_INSTALLATION_ID"]

print(f"[OK] App ID: {app_id}")
print(f"[OK] Installation ID: {install_id}")
print(f"[OK] PEM key loaded: {len(pem)} chars")

# Sign JWT
now = int(time.time())
payload = {
    "iat": now - 60,
    "exp": now + 600,
    "iss": app_id,
}
jwt_token = jwt.encode(payload, pem, algorithm="RS256")
print(f"[OK] JWT signed: {len(jwt_token)} chars")

# Exchange for installation token
resp = requests.post(
    f"https://api.github.com/app/installations/{install_id}/access_tokens",
    headers={
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json",
    },
    timeout=30,
)
resp.raise_for_status()
token = resp.json()["token"]
print(f"[OK] Installation token received: {token[:20]}...")
print("  Token expires in 1 hour (rate limit: 5000/hour)")

# Test token with GitHub API
test_resp = requests.get(
    "https://api.github.com/orgs/POWERFULMOVES/repos",
    headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    },
    timeout=30,
)
print(f"[OK] GitHub API test: {test_resp.status_code}")
repos = test_resp.json()
print(f"[OK] Found {len(repos)} repositories")

# List first few repos
for repo in repos[:5]:
    print(f"  - {repo['name']}")
