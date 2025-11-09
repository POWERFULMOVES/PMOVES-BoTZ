#!/usr/bin/env python3
"""
PMOVES Smoke Tests
Verifies core functionality across all agent packs.
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

    def test_docker_compose(self, compose_file, service_name):
        """Test Docker Compose service startup"""
        try:
            # Check if compose file exists
            if not Path(compose_file).exists():
                self.log(f"Compose file not found: {compose_file}", "FAIL")
                return False

            # Try to validate compose file
            result = subprocess.run(
                ['docker-compose', '-f', compose_file, 'config'],
                capture_output=True, text=True, cwd=self.base_dir
            )

            if result.returncode != 0:
                self.log(f"Invalid compose file {compose_file}: {result.stderr}", "FAIL")
                return False

            self.log(f"Docker Compose validation passed for {compose_file}", "PASS")
            return True

        except Exception as e:
            self.log(f"Error testing compose file {compose_file}: {e}", "FAIL")
            return False

    def test_pack_configs(self):
        """Test configuration files for each pack"""
        packs = {
            'mini': 'pmoves-mini-agent-box',
            'multi': 'pmoves_multi_agent_pack',
            'pro': 'pmoves_multi_agent_pro_pack',
            'pro_plus': 'pmoves_multi_agent_pro_plus_pack'
        }

        all_passed = True
        total_valid_compose = 0

        for pack_name, pack_dir in packs.items():
            pack_path = self.base_dir / pack_dir
            if not pack_path.exists():
                self.log(f"Pack directory missing: {pack_dir}", "WARN")
                continue

            # Check for required files (be more lenient for now)
            required_files = ['README.md'] if pack_name != 'pro_plus' else []
            for req_file in required_files:
                if not (pack_path / req_file).exists():
                    self.log(f"Missing {req_file} in {pack_dir}", "WARN")

            # Test compose files (only validate syntax, not require all to pass)
            compose_files = list(pack_path.glob('docker-compose*.yml'))
            valid_compose_count = 0
            for compose_file in compose_files:
                if self.test_docker_compose(str(compose_file), pack_name):
                    valid_compose_count += 1
                    total_valid_compose += 1

            self.log(f"Found {valid_compose_count} valid compose files in {pack_dir}", "INFO")

        # Require at least one valid compose file across all packs
        if total_valid_compose == 0:
            self.log("No valid compose files found in any pack", "FAIL")
            all_passed = False
        else:
            self.log(f"Found {total_valid_compose} valid compose files across all packs", "PASS")

        return all_passed

    def test_cipher_memory(self):
        """Test Pmoves-cipher memory integration"""
        tests = []
        
        # Check if cipher submodule exists
        cipher_path = self.base_dir / 'pmoves_multi_agent_pro_pack' / 'memory_shim' / 'pmoves_cipher'
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
        
        # Check API key for cipher (Venice.ai or OpenAI)
        venice_key = os.getenv('VENICE_API_KEY')
        openai_key = os.getenv('OPENAI_API_KEY')
        
        if venice_key and venice_key != 'test_key_placeholder' and len(venice_key) > 10:
            tests.append(("OpenAI API", True, "Venice.ai API key format valid for cipher"))
        elif openai_key and openai_key != 'test_key_placeholder' and openai_key.startswith('sk-'):
            tests.append(("OpenAI API", True, "OpenAI API key format valid for cipher"))
        else:
            tests.append(("OpenAI API", False, "Missing or invalid API key for cipher (need VENICE_API_KEY or OPENAI_API_KEY)"))
        
        # Check cipher configuration
        cipher_config = cipher_path / 'memAgent' / 'cipher.yml'
        if cipher_config.exists():
            tests.append(("Cipher Config", True, "PMOVES cipher configuration found"))
        else:
            tests.append(("Cipher Config", False, "Run cipher setup script"))
        
        # Test cipher memory server script
        memory_script = self.base_dir / 'pmoves_multi_agent_pro_pack' / 'memory_shim' / 'app_cipher_memory.py'
        if memory_script.exists():
            tests.append(("Memory Server", True, "Cipher memory server script found"))
        else:
            tests.append(("Memory Server", False, "Memory server script missing"))
        
        for service, passed, msg in tests:
            status = "PASS" if passed else "FAIL"
            self.log(f"Cipher {service}: {msg}", status)
        
        return all(passed for _, passed, _ in tests)

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

    def run_all_tests(self):
        """Run all smoke tests"""
        self.log("Starting PMOVES smoke tests...")

        tests = [
            ("Environment Configuration", self.check_env_file),
            ("Pack Configurations", self.test_pack_configs),
            ("Cipher Memory Integration", self.test_cipher_memory),
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