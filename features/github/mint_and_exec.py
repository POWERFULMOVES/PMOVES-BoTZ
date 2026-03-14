"""GitHub App token minter + MCP server launcher.

Mints a short-lived GitHub App installation token, then execs
the upstream @modelcontextprotocol/server-github MCP server.

Required env:
    GH_APP_ID              - GitHub App numeric ID
    GH_APP_SEC             - PEM private key (full contents)
    GH_APP_INSTALLATION_ID - Installation ID for the org

The minted token is set as GITHUB_PERSONAL_ACCESS_TOKEN before
exec-ing the MCP server, so it has org-wide access to all repos
under the installation.
"""

import codecs
import os
import subprocess
import sys
import time

import jwt
import requests


def _unescape_env_value(value: str) -> str:
    """Unescape a value that was escaped for env file storage.

    Handles the double-escaping from secrets_sync.py:
    - First layer: remove outer quotes from env file format
    - Second layer: convert escape sequences (\\n, \\", etc.) to actual chars

    The env.tier-agent file stores values as: "value" where value contains:
    - \" for literal quotes
    - \\n for literal newlines
    - \\\\ for literal backslashes
    """
    if not value:
        return value

    # Remove surrounding quotes if present
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]

    # Handle nested escaping (secrets_sync.py adds extra layer)
    # Order: replace escaped sequences first, then escaped quotes
    if "\\\\n" in value or "\\\\" in value or '\\"' in value:
        result = value
        # Replace escaped escape sequences first
        result = result.replace("\\\\n", "\n")   # \\n -> newline
        result = result.replace("\\\\r", "\r")   # \\r -> carriage return
        result = result.replace("\\\\t", "\t")   # \\t -> tab
        result = result.replace("\\\\\\\\", "\\")  # \\\\ -> single backslash
        # Then replace escaped quotes
        result = result.replace('\\"', '"')      # \" -> "
        return result

    # Single-layer escaping fallback
    if "\\n" in value or "\\\\" in value:
        try:
            return codecs.decode(value, "unicode_escape")
        except Exception:
            result = value
            result = result.replace("\\n", "\n")
            result = result.replace("\\r", "\r")
            result = result.replace("\\t", "\t")
            result = result.replace('\\"', '"')
            result = result.replace("\\\\", "\\")
            return result

    return value


def mint_installation_token() -> str:
    """Mint a short-lived GitHub App installation token.

    Signs a JWT with the App's PEM key, then exchanges it for an
    installation access token via the GitHub API. The token expires
    after 1 hour.

    Returns:
        str: Installation access token.

    Raises:
        KeyError: If required env vars are missing.
        requests.HTTPError: If the GitHub API call fails.
    """
    app_id = os.environ["GH_APP_ID"]
    pem = _unescape_env_value(os.environ["GH_APP_SEC"])
    install_id = os.environ["GH_APP_INSTALLATION_ID"]

    now = int(time.time())
    # GitHub requires: exp - iat <= 600 seconds (10 minutes max JWT lifetime)
    payload = {
        "iat": now - 30,   # issued 30s ago for clock skew tolerance
        "exp": now + 570,  # expires 9.5min from now (total lifetime < 10 min)
        "iss": app_id,
    }
    jwt_token = jwt.encode(payload, pem, algorithm="RS256")

    resp = requests.post(
        f"https://api.github.com/app/installations/{install_id}/access_tokens",
        headers={
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["token"]


def main() -> None:
    """Mint token and exec the upstream MCP server."""
    token = mint_installation_token()
    os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = token

    if sys.platform == "win32":
        # Windows lacks execvp; use subprocess as fallback
        result = subprocess.run(
            ["npx", "-y", "@modelcontextprotocol/server-github"],
            env=os.environ,
        )
        sys.exit(result.returncode)
    else:
        os.execvp("npx", ["npx", "-y", "@modelcontextprotocol/server-github"])


if __name__ == "__main__":
    main()
