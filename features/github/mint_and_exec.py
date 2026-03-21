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

import os
import subprocess
import sys
import time

import jwt
import requests


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
    pem = os.environ["GH_APP_SEC"]
    install_id = os.environ["GH_APP_INSTALLATION_ID"]

    now = int(time.time())
    payload = {
        "iat": now - 60,   # issued at (60s clock skew tolerance)
        "exp": now + 600,  # expires in 10 minutes
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

    # Build clean env: inject minted token, strip App secrets
    child_env = {k: v for k, v in os.environ.items()
                 if k not in ("GH_APP_SEC", "GH_APP_ID", "GH_APP_INSTALL_ID")}
    child_env["GITHUB_PERSONAL_ACCESS_TOKEN"] = token

    if sys.platform == "win32":
        # Windows lacks execvp; use subprocess as fallback
        result = subprocess.run(
            ["npx", "-y", "@modelcontextprotocol/server-github"],
            env=child_env,
        )
        sys.exit(result.returncode)
    else:
        os.environ.clear()
        os.environ.update(child_env)
        os.execvp("npx", ["npx", "-y", "@modelcontextprotocol/server-github"])


if __name__ == "__main__":
    main()
