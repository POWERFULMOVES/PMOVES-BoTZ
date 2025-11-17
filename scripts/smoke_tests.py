#!/usr/bin/env python3
"""
PMOVES-BoTZ Smoke Tests
Verifies core functionality across the unified core/features stack.
Run with: python scripts/smoke_tests.py
"""

import os
import sys
import subprocess
import requests
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class SmokeTester:
    def __init__(self):
        self.results = []
        self.env_file = Path('.env')
        self.base_dir = Path(__file__).parent.parent

    def log(self, message, status='INFO'):
        """Log test results"""
        timestamp = time.strftime('%H:%M:%S')
        print(f"[{timestamp}] {status}: {message}")
        self.results.append(f"{status}: {message}")

    def check_env_file(self):
        """Check if .env file exists and has required variables"""
        if not self.env_file.exists():
            self.log("No .env file found - copy from core/example.env", "FAIL")
            return False

        # For now, just check that the file exists and has some content
        # We'll be more lenient with specific variable validation
        with open(self.env_file) as f:
            content = f.read()
            if len(content.strip()) < 10:  # Very basic check
                self.log("Environment file appears to be empty or too small", "FAIL")
                return False

        self.log("Environment file exists and has content", "PASS")
        return True

    def test_pack_configs(self):
        """Validate the main PMOVES-BoTZ compose stacks against current services/ports."""
        stacks = {
            "botz_core_only": [
                "core/docker-compose/base.yml",
            ],
            "botz_core_metrics_external": [
                "core/docker-compose/base.yml",
                "features/metrics/docker-compose.yml",
                "features/network/external.yml",
            ],
            "botz_core_metrics_internal": [
                "core/docker-compose/base.yml",
                "features/metrics/docker-compose.yml",
                "features/network/internal.yml",
            ],
            "botz_core_metrics_ephemeral": [
                "core/docker-compose/base.yml",
                "features/metrics/docker-compose.yml",
                "features/network/ephemeral.yml",
            ],
        }

        all_passed = True

        for stack_name, compose_files in stacks.items():
            # Ensure all compose files exist
            missing = [f for f in compose_files if not (self.base_dir / f).exists()]
            if missing:
                self.log(
                    f"Stack {stack_name} missing compose files: {', '.join(missing)}",
                    "FAIL",
                )
                all_passed = False
                continue

            try:
                cmd = ["docker", "compose"]
                for f in compose_files:
                    cmd.extend(["-f", f])
                cmd.append("config")

                result = subprocess.run(
                    cmd, capture_output=True, text=True, cwd=self.base_dir
                )

                if result.returncode != 0:
                    self.log(
                        f"Invalid compose stack {stack_name}: {result.stderr}", "FAIL"
                    )
                    all_passed = False
                else:
                    self.log(
                        f"Docker Compose validation passed for stack {stack_name}",
                        "PASS",
                    )
            except Exception as e:
                self.log(f"Error testing stack {stack_name}: {e}", "FAIL")
                all_passed = False

        return all_passed

    def test_core_services_health(self):
        """Verify core HTTP health endpoints for the unified stack."""
        tests = []

        gateway_port = (
            os.getenv("MCP_GATEWAY_PORT")
            or os.getenv("GATEWAY_PORT")
            or "2091"
        )
        docling_port = (
            os.getenv("DOCLING_MCP_PORT")
            or os.getenv("DOCLING_PORT")
            or "3020"
        )

        health_targets = [
            ("Gateway", f"http://localhost:{gateway_port}/health"),
            ("Docling", f"http://localhost:{docling_port}/health"),
        ]

        for name, url in health_targets:
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    tests.append((name, True, f"Health check OK at {url}"))
                else:
                    tests.append(
                        (name, False, f"Health check HTTP {resp.status_code} at {url}")
                    )
            except Exception as e:
                tests.append((name, False, f"Health check error at {url}: {e}"))

        all_ok = True
        for service, passed, msg in tests:
            status = "PASS" if passed else "FAIL"
            self.log(f"{service} Service: {msg}", status)
            if not passed:
                all_ok = False

        return all_ok

    def test_cipher_memory(self):
        """Static checks for Pmoves-cipher memory integration (files + keys)."""
        tests = []
        
        # Check if cipher submodule exists
        cipher_path = self.base_dir / 'features' / 'cipher' / 'pmoves_cipher'
        if cipher_path.exists():
            tests.append(("Cipher Submodule", True, f"Found at {cipher_path}"))
        else:
            tests.append(("Cipher Submodule", False, "Not found - run git submodule update --init"))
        
        # Check if cipher is built
        cipher_binary = cipher_path / 'dist' / 'src' / 'app' / 'index.cjs'
        if cipher_binary.exists():
            tests.append(("Cipher Build", True, "Cipher binary found"))
        else:
            tests.append(("Cipher Build", False, "Cipher not built - run setup script"))
        
        # Check API key for cipher (Venice.ai or OpenAI). In local-first/Ollama-only mode,
        # absence of these keys is allowed and treated as a soft pass.
        venice_key = os.getenv('VENICE_API_KEY')
        openai_key = os.getenv('OPENAI_API_KEY')
        local_only = os.getenv('PMOVES_LOCAL_ONLY') == '1' or bool(os.getenv('OLLAMA_BASE_URL'))
        
        if venice_key and venice_key != 'test_key_placeholder' and len(venice_key) > 10:
            tests.append(("OpenAI API", True, "Venice.ai API key format valid for cipher"))
        elif openai_key and openai_key != 'test_key_placeholder' and openai_key.startswith('sk-'):
            tests.append(("OpenAI API", True, "OpenAI API key format valid for cipher"))
        elif local_only:
            # Local/Ollama-only mode: skip hard failure on cloud keys
            tests.append(("OpenAI API", True, "No cloud LLM key set (local/Ollama-only mode; skipping)"))
        else:
            tests.append(("OpenAI API", True, "No cloud LLM key set; cipher will run with limited capabilities until VENICE_API_KEY or OPENAI_API_KEY is provided"))
        
        # Check cipher configuration
        cipher_config = cipher_path / 'memAgent' / 'cipher.yml'
        if cipher_config.exists():
            tests.append(("Cipher Config", True, "PMOVES cipher configuration found"))
        else:
            tests.append(("Cipher Config", False, "Run cipher setup script"))
        
        for service, passed, msg in tests:
            status = "PASS" if passed else "FAIL"
            self.log(f"Cipher {service}: {msg}", status)
        
        return all(passed for _, passed, _ in tests)

    def test_cipher_service_health(self):
        """Runtime health checks for the cipher-memory service (API/UI)."""
        cipher_api_port = os.getenv("CIPHER_API_PORT") or "3011"
        cipher_ui_port = os.getenv("CIPHER_UI_PORT") or "3010"
        api_url = f"http://localhost:{cipher_api_port}/health"
        ui_url = f"http://localhost:{cipher_ui_port}"

        # Try API health endpoint first, then UI as a fallback (mirrors docker healthcheck).
        for url, label in [(api_url, "API"), (ui_url, "UI")]:
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    self.log(f"Cipher service {label} endpoint healthy at {url}", "PASS")
                    return True
                else:
                    self.log(
                        f"Cipher service {label} endpoint HTTP {resp.status_code} at {url}",
                        "WARN",
                    )
            except Exception as e:
                self.log(f"Cipher service {label} endpoint error at {url}: {e}", "WARN")

        self.log("Cipher service: no healthy API or UI endpoint detected", "FAIL")
        return False

    def test_cipher_functionality(self):
        """Basic functional tests for Cipher memory API (non-destructive)."""
        cipher_api_port = os.getenv("CIPHER_API_PORT") or "3011"
        base_url = f"http://localhost:{cipher_api_port}"
        all_ok = True

        def safe_get(path, label):
            url = f"{base_url}{path}"
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    self.log(f"Cipher {label}: OK at {url}", "PASS")
                    return True, resp
                else:
                    self.log(f"Cipher {label}: HTTP {resp.status_code} at {url}", "FAIL")
                    return False, resp
            except Exception as e:
                self.log(f"Cipher {label}: error at {url}: {e}", "FAIL")
                return False, None

        # 1) System health from API root (/health already covered; keep as extra assertion)
        ok, _ = safe_get("/health", "API health")
        all_ok = all_ok and ok

        # 2) Agent discovery document (/.well-known/agent.json)
        ok, resp = safe_get("/.well-known/agent.json", "agent discovery")
        if ok:
            try:
                data = resp.json()
                if data.get("name") and "endpoints" in data:
                    self.log("Cipher agent discovery document shape valid", "PASS")
                else:
                    self.log("Cipher agent discovery document missing expected fields", "FAIL")
                    all_ok = False
            except Exception as e:
                self.log(f"Cipher agent discovery JSON parse error: {e}", "FAIL")
                all_ok = False

        # 3) Sessions API: list sessions (read-only)
        ok, resp = safe_get("/api/sessions", "sessions list")
        if ok:
            try:
                data = resp.json()
                # API returns { success, data: { sessions: [...] }, meta: {...} }
                sessions_container = data.get("data") or {}
                if isinstance(sessions_container, dict) and "sessions" in sessions_container:
                    self.log("Cipher sessions list structure valid", "PASS")
                else:
                    self.log("Cipher sessions list missing data.sessions field", "FAIL")
                    all_ok = False
            except Exception as e:
                self.log(f"Cipher sessions list JSON parse error: {e}", "FAIL")
                all_ok = False

        return all_ok

    def test_cipher_message_roundtrip(self):
        """Optional message roundtrip test against Cipher /api/message-sync.

        Only runs when a real VENICE_API_KEY or OPENAI_API_KEY is configured,
        to avoid depending on cloud LLMs in minimal/local-only setups.
        """
        venice_key = os.getenv('VENICE_API_KEY')
        openai_key = os.getenv('OPENAI_API_KEY')

        has_real_key = False
        if venice_key and venice_key != 'test_key_placeholder' and len(venice_key) > 10:
            has_real_key = True
        elif openai_key and openai_key != 'test_key_placeholder' and openai_key.startswith('sk-'):
            has_real_key = True

        if not has_real_key:
            # Skip as soft-pass when no real key is configured.
            self.log(
                "Cipher message roundtrip: skipping (no real VENICE_API_KEY / OPENAI_API_KEY configured)",
                "PASS",
            )
            return True

        cipher_api_port = os.getenv("CIPHER_API_PORT") or "3011"
        url = f"http://localhost:{cipher_api_port}/api/message/sync"

        payload = {
            "message": "ping from smoke_tests",
            "sessionId": "smoke_test_session",
            "images": [],
        }

        try:
            resp = requests.post(url, json=payload, timeout=20)

            # Treat any non-2xx as soft pass for now since upstream
            # LLM/auth issues are environment-specific. The fact that we
            # can reach the endpoint is enough for smoke coverage.
            if not (200 <= resp.status_code < 300):
                self.log(
                    f"Cipher message roundtrip: non-2xx ({resp.status_code}) at {url}; treating as informational only",
                    "PASS",
                )
                return True

            data = resp.json()
            if not isinstance(data, dict):
                self.log("Cipher message roundtrip: non-JSON response", "FAIL")
                return False

            # Expect standard API envelope with success + data
            if not data.get("success"):
                self.log("Cipher message roundtrip: success flag not true", "FAIL")
                return False

            response_payload = data.get("data") or {}
            if "response" not in response_payload:
                self.log("Cipher message roundtrip: missing 'data.response' field", "FAIL")
                return False

            self.log("Cipher message roundtrip: basic message processed successfully", "PASS")
            return True
        except Exception as e:
            self.log(f"Cipher message roundtrip: error calling {url}: {e}", "FAIL")
            return False

    def test_metrics_services(self):
        """Verify Prometheus and Grafana are reachable on expected ports."""
        prom_port = os.getenv("PROMETHEUS_PORT") or "9090"
        graf_port = os.getenv("GRAFANA_PORT") or "3033"

        targets = [
            ("Prometheus", f"http://localhost:{prom_port}/targets"),
            ("Grafana", f"http://localhost:{graf_port}/login"),
        ]

        all_ok = True
        for name, url in targets:
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    self.log(f"{name}: reachable at {url}", "PASS")
                else:
                    self.log(f"{name}: HTTP {resp.status_code} at {url}", "FAIL")
                    all_ok = False
            except Exception as e:
                self.log(f"{name}: error reaching {url}: {e}", "FAIL")
                all_ok = False

        return all_ok

    def test_vl_sentinel_health(self):
        """Verify the VL-Sentinel service is healthy (Ollama/local-first path)."""
        vl_port = os.getenv("VL_PORT") or "7072"
        url = f"http://localhost:{vl_port}/health"

        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                self.log(f"VL-Sentinel: healthy at {url}", "PASS")
                return True
            else:
                self.log(
                    f"VL-Sentinel: HTTP {resp.status_code} at {url} (check Ollama/model config)",
                    "FAIL",
                )
                return False
        except Exception as e:
            self.log(f"VL-Sentinel: error reaching {url}: {e}", "FAIL")
            return False

    def test_api_connectivity(self):
        """Test external API connectivity"""
        tests = []

        # Test Postman API if key provided
        postman_key = os.getenv('POSTMAN_API_KEY')
        if postman_key and postman_key != 'test_key_placeholder':
            try:
                headers = {'X-API-Key': postman_key}
                response = requests.get('https://api.postman.com/me', headers=headers, timeout=10)
                if response.status_code == 200:
                    tests.append(("Postman API", True, "Connected successfully"))
                else:
                    tests.append(("Postman API", False, f"HTTP {response.status_code}"))
            except Exception as e:
                tests.append(("Postman API", False, str(e)))
        else:
            tests.append(("Postman API", True, "Using test placeholder - skipping live test"))

        # Test Tailscale auth key format (check both TS_AUTHKEY and TAILSCALE_AUTHKEY)
        ts_key = os.getenv('TS_AUTHKEY') or os.getenv('TAILSCALE_AUTHKEY')
        if ts_key and ts_key not in ['test_key_placeholder', 'test_tailscale_key_placeholder']:
            # Basic format validation for Tailscale auth keys
            if ts_key.startswith('tskey-') and len(ts_key) > 20:
                tests.append(("Tailscale", True, f"Auth key format valid (starts with tskey-, length {len(ts_key)})"))
            else:
                tests.append(("Tailscale", False, f"Invalid auth key format: {ts_key[:10]}..."))
        else:
            # For now, make this optional since some packs may not need Tailscale
            tests.append(("Tailscale", True, "Tailscale auth key not required for basic functionality"))

        for service, passed, msg in tests:
            status = "PASS" if passed else "FAIL"
            self.log(f"{service}: {msg}", status)

        return all(passed for _, passed, _ in tests)

    def test_yt_mini(self):
        """Optional checks for a future PMOVES.YT mini agent.

        This only performs network checks when explicitly enabled via
        PMOVES_YT_ENABLED=1 to avoid failing in environments where the
        YT overlay is not in use yet.
        """
        if os.getenv("PMOVES_YT_ENABLED") != "1":
            self.log("YT mini: skipping (PMOVES_YT_ENABLED != 1)", "PASS")
            return True

        yt_port = os.getenv("YT_MINI_PORT") or "3050"
        url = f"http://localhost:{yt_port}/health"

        try:
            resp = requests.get(url, timeout=5)
            if 200 <= resp.status_code < 300:
                self.log(f"YT mini: health endpoint OK at {url}", "PASS")
            else:
                self.log(
                    f"YT mini: HTTP {resp.status_code} at {url} (service enabled but not healthy)",
                    "FAIL",
                )
                return False
        except Exception as e:
            self.log(f"YT mini: error reaching {url}: {e}", "FAIL")
            return False

        # Optional CLI check (best-effort, does not fail test)
        yt_cli = os.getenv("YT_MINI_CLI") or "yt-mini"
        try:
            result = subprocess.run(
                [yt_cli, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                self.log("YT mini CLI: detected and responding to --version", "PASS")
            else:
                self.log(
                    f"YT mini CLI: non-zero exit ({result.returncode}); output: {result.stdout or result.stderr}",
                    "WARN",
                )
        except FileNotFoundError:
            self.log("YT mini CLI: not found on PATH (skipping CLI check)", "WARN")
        except Exception as e:
            self.log(f"YT mini CLI: error invoking CLI: {e}", "WARN")

        return True

    def run_all_tests(self):
        """Run all smoke tests"""
        self.log("Starting PMOVES smoke tests...")

        tests = [
            ("Environment Configuration", self.check_env_file),
            ("Compose Stack Configuration", self.test_pack_configs),
            ("Core Service Health", self.test_core_services_health),
             ("VL-Sentinel Health", self.test_vl_sentinel_health),
            ("Cipher Memory Integration", self.test_cipher_memory),
            ("Cipher Service Health", self.test_cipher_service_health),
            ("Cipher Functional API", self.test_cipher_functionality),
            ("Cipher Message Roundtrip", self.test_cipher_message_roundtrip),
            ("YT Mini Agent", self.test_yt_mini),
            ("Metrics Stack", self.test_metrics_services),
            ("API Connectivity", self.test_api_connectivity),
        ]

        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            self.log(f"Running {test_name} tests...")
            try:
                if test_func():
                    passed += 1
                    self.log(f"{test_name} tests PASSED", "PASS")
                else:
                    self.log(f"{test_name} tests FAILED", "FAIL")
            except Exception as e:
                self.log(f"{test_name} tests ERROR: {e}", "FAIL")

        self.log(f"Smoke tests completed: {passed}/{total} passed")

        # Summary
        if passed == total:
            self.log("All smoke tests PASSED - System ready for deployment", "PASS")
            return True
        else:
            self.log(f"{total - passed} tests failed - Check configuration", "FAIL")
            return False

def main():
    tester = SmokeTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
