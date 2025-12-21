#!/usr/bin/env python3
"""
LMS API Integration Demo for PMOVES-BoTZ

This script demonstrates connecting to MCP services and testing API integration.
It adapts to the 5-Tier Network Architecture where only the Gateway and TensorZero are exposed.
"""

import os
import sys
import json
import time
import requests
from datetime import datetime

# Configuration
LMS_API_HOST = "localhost:52379"
LMS_API_BASE_URL = f"http://{LMS_API_HOST}/api/v2"

# Test credentials
API_KEY = os.getenv("LMS_API_KEY", "test-api-key")
SECRET_KEY = os.getenv("LMS_SECRET_KEY", "test-secret-key")

# Service Map (Publicly Exposed)
PUBLIC_SERVICES = {
    "mcp-gateway": "http://localhost:2091/health",
    "tensorzero": "http://localhost:3006/health"
}

# Service Map (Internal - Expected to be unreachable from Host in Prod, but maybe checkable via Gateway)
INTERNAL_SERVICES = {
    "docling-mcp": "http://localhost:3020",
    "e2b-runner": "http://localhost:7071",
    "vl-sentinel": "http://localhost:7072"
}

def log(message):
    """Print timestamped log message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Replace Unicode characters with ASCII equivalents for Windows compatibility
    message = message.replace("✅", "[PASS]").replace("❌", "[FAIL]").replace("⚠️", "[WARN]").replace("ℹ️", "[INFO]")
    print(f"[{timestamp}] {message}")

def test_connection():
    """Test connection to services"""
    log("=== Testing Public Service Connectivity ===")
    
    all_passed = True
    
    # 1. Check Public Services (Must Pass)
    for service_name, health_url in PUBLIC_SERVICES.items():
        try:
            response = requests.get(health_url, timeout=5)
            if response.status_code == 200:
                log(f"✅ [PASS] {service_name} is accessible")
            else:
                log(f"❌ [FAIL] {service_name} returned status {response.status_code}")
                all_passed = False
        except requests.exceptions.RequestException:
            log(f"❌ [FAIL] {service_name} is unreachable at {health_url}")
            all_passed = False

    # 2. Check Internal Services (Informational)
    log("=== Checking Internal Services (Host Access) ===")
    for service_name, health_url in INTERNAL_SERVICES.items():
        try:
            requests.get(health_url, timeout=2)
            # In Development mode, these SHOULD be accessible
            log(f"✅ [PASS] {service_name} is accessible from host (Dev Mode Integration)")
        except requests.exceptions.RequestException:
            # In Production, this is good. In Dev, it might imply services aren't running.
            log(f"ℹ️  [INFO] {service_name} is not accessible from host (Production Segregation or Service Down)")


    return all_passed

def authenticate():
    """Authenticate with LMS API (Optional)"""
    if "test-" in API_KEY:
        log("ℹ️  [INFO] Skipping LMS Auth (Default/Test Keys detected)")
        return None

    log("=== Authenticating with LMS API ===")
    try:
        response = requests.post(f"{LMS_API_BASE_URL}/login", 
                               json={"request": {"apiKey": API_KEY, "secretKey": SECRET_KEY}}, 
                               timeout=5)
        if response.status_code == 200 and response.json().get("result"):
            token = response.json().get("token", "")
            log(f"✅ [PASS] Auth successful")
            return token
        log(f"❌ [FAIL] Auth failed: {response.text}")
    except Exception as e:
        log(f"⚠️  [WARN] LMS API unreachable: {e}")
    return None

def main():
    """Main execution function"""
    log("Starting PMOVES-BoTZ API Integration Demo")
    
    if not test_connection():
        log("❌ [FAIL] Critical services are down. Check docker logs.")
        return 1
        
    authenticate()
    
    log("Demo completed.")
    return 0

if __name__ == "__main__":
    sys.exit(main())