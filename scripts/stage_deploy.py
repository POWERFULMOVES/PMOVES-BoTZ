#!/usr/bin/env python3
"""
PMOVES Staging Deployment Script
Deploys and verifies agent packs in staging environment.
Usage: python scripts/stage_deploy.py [pack_name]
Packs: mini, multi, pro, pro_plus
"""

import os
import sys
import subprocess
import time
import argparse
from pathlib import Path
from smoke_tests import SmokeTester

class StageDeployer:
    def __init__(self, pack_name=None):
        self.pack_name = pack_name
        self.base_dir = Path(__file__).parent.parent
        self.smoke_tester = SmokeTester()

    def log(self, message, status='INFO'):
        """Log deployment progress"""
        timestamp = time.strftime('%H:%M:%S')
        print(f"[{timestamp}] {status}: {message}")

    def get_pack_config(self, pack_name):
        """Get pack-specific configuration"""
        packs = {
            'mini': {
                'dir': 'pmoves-mini-agent-box',
                'compose_files': ['docker-compose.pmoves-mini.staging.yml'],
                'services': ['crush-shim', 'discord-bot'],
                'health_checks': []
            },
            'multi': {
                'dir': 'pmoves_multi_agent_pack',
                'compose_files': ['docker-compose.pmoves-multi.yml'],
                'services': ['docling-mcp', 'postman-mcp'],
                'health_checks': ['http://localhost:3020/health', 'http://localhost:3021/health']
            },
            'pro': {
                'dir': 'pmoves_multi_agent_pro_pack',
                'compose_files': ['docker-compose.mcp-pro.yml'],
                'services': ['e2b-shim', 'vl-sentinel'],
                'health_checks': ['http://localhost:3022/health', 'http://localhost:3023/health']
            },
            'pro_plus': {
                'dir': 'pmoves_multi_agent_pro_plus_pack',
                'compose_files': ['docker-compose.mcp-pro.local-postman.yml', 'docker-compose.mcp-pro.vlm.yml'],
                'services': ['postman-mcp-local', 'docling-mcp'],
                'health_checks': ['http://localhost:3024/health']
            }
        }
        return packs.get(pack_name)

    def run_pre_deploy_checks(self):
        """Run pre-deployment validation"""
        self.log("Running pre-deployment checks...")

        # Run smoke tests
        if not self.smoke_tester.run_all_tests():
            self.log("Smoke tests failed - aborting deployment", "FAIL")
            return False

        self.log("Pre-deployment checks passed", "PASS")
        return True

    def deploy_pack(self, pack_config):
        """Deploy a specific pack"""
        pack_dir = self.base_dir / pack_config['dir']

        if not pack_dir.exists():
            self.log(f"Pack directory not found: {pack_dir}", "FAIL")
            return False

        os.chdir(pack_dir)

        # Stop any existing services
        self.log("Stopping existing services...")
        for compose_file in pack_config['compose_files']:
            if Path(compose_file).exists():
                subprocess.run(['docker-compose', '-f', compose_file, 'down'],
                             capture_output=True)

        # Start services
        self.log("Starting services...")
        for compose_file in pack_config['compose_files']:
            if Path(compose_file).exists():
                result = subprocess.run(['docker-compose', '-f', compose_file, 'up', '-d'],
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    self.log(f"Failed to start services from {compose_file}: {result.stderr}", "FAIL")
                    return False

        # Wait for services to be ready
        self.log("Waiting for services to be ready...")
        time.sleep(10)

        # Check service health
        healthy = True
        for health_url in pack_config['health_checks']:
            try:
                import requests
                response = requests.get(health_url, timeout=5)
                if response.status_code != 200:
                    self.log(f"Health check failed for {health_url}: HTTP {response.status_code}", "WARN")
                    healthy = False
            except Exception as e:
                self.log(f"Health check error for {health_url}: {e}", "WARN")
                healthy = False

        if healthy:
            self.log("All health checks passed", "PASS")
        else:
            self.log("Some health checks failed - manual verification required", "WARN")

        return True

    def run_post_deploy_tests(self, pack_config):
        """Run post-deployment verification"""
        self.log("Running post-deployment tests...")

        # Check Docker services are running
        for compose_file in pack_config['compose_files']:
            if Path(compose_file).exists():
                result = subprocess.run(['docker-compose', '-f', compose_file, 'ps'],
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    self.log(f"Services not running from {compose_file}", "FAIL")
                    return False

                # Check if expected services are listed
                for service in pack_config['services']:
                    if service not in result.stdout:
                        self.log(f"Service {service} not found in running containers", "WARN")

        self.log("Post-deployment tests completed", "PASS")
        return True

    def deploy_all_packs(self):
        """Deploy all packs sequentially"""
        packs = ['mini', 'multi', 'pro', 'pro_plus']
        results = {}

        for pack in packs:
            self.log(f"Deploying {pack} pack...")
            pack_config = self.get_pack_config(pack)
            if not pack_config:
                self.log(f"Unknown pack: {pack}", "FAIL")
                results[pack] = False
                continue

            try:
                if self.deploy_pack(pack_config) and self.run_post_deploy_tests(pack_config):
                    results[pack] = True
                    self.log(f"{pack} pack deployed successfully", "PASS")
                else:
                    results[pack] = False
                    self.log(f"{pack} pack deployment failed", "FAIL")
            except Exception as e:
                self.log(f"Error deploying {pack}: {e}", "FAIL")
                results[pack] = False

        return results

    def run_deployment(self):
        """Main deployment orchestration"""
        if not self.run_pre_deploy_checks():
            return False

        if self.pack_name:
            # Deploy single pack
            pack_config = self.get_pack_config(self.pack_name)
            if not pack_config:
                self.log(f"Unknown pack: {self.pack_name}", "FAIL")
                return False

            success = self.deploy_pack(pack_config) and self.run_post_deploy_tests(pack_config)
        else:
            # Deploy all packs
            results = self.deploy_all_packs()
            success = all(results.values())

            # Summary
            self.log("Deployment Summary:")
            for pack, result in results.items():
                status = "PASS" if result else "FAIL"
                self.log(f"  {pack}: {status}")

        return success

def main():
    parser = argparse.ArgumentParser(description='PMOVES Staging Deployment')
    parser.add_argument('pack', nargs='?', help='Pack to deploy (mini, multi, pro, pro_plus)')
    args = parser.parse_args()

    deployer = StageDeployer(args.pack)
    success = deployer.run_deployment()

    if success:
        print("\n[SUCCESS] Staging deployment completed successfully!")
        print("Run 'python scripts/smoke_tests.py' to verify functionality")
    else:
        print("\n[FAILED] Staging deployment failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()