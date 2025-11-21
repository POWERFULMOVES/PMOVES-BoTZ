#!/usr/bin/env python3
"""
LMS API Integration Demo for PMOVES-Kilobots

This script demonstrates connecting to MCP services and testing LMS API integration.
It will:
1. Connect to running MCP services
2. Test API requests through the gateway
3. Verify response data matches LMS schema
4. Report any issues
"""

import os
import sys
import json
import time
import requests
from datetime import datetime

# Configuration
LMS_API_HOST = "localhost:52379"  # Default from collections_api_v2_0.json
LMS_API_BASE_URL = f"http://{LMS_API_HOST}/api/v2"

# Test credentials (these would normally come from environment variables)
API_KEY = "test-api-key"
SECRET_KEY = "test-secret-key"

def log(message):
    """Print timestamped log message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def test_connection():
    """Test if we can connect to MCP services"""
    log("=== Testing MCP Service Connection ===")
    
    # Test if cipher memory is accessible
    try:
        response = requests.get("http://localhost:7070/health", timeout=5)
        if response.status_code == 200:
            log("✅ PASS: Cipher Memory service is accessible")
        else:
            log(f"❌ FAIL: Cipher Memory service returned status {response.status_code}")
    except requests.exceptions.RequestException as e:
        log(f"❌ FAIL: Could not connect to Cipher Memory service: {e}")
    
    # Test if auto-research service is accessible
    try:
        response = requests.get("http://localhost:7071/health", timeout=5)
        if response.status_code == 200:
            log("✅ PASS: Auto-Research service is accessible")
        else:
            log(f"❌ FAIL: Auto-Research service returned status {response.status_code}")
    except requests.exceptions.RequestException as e:
        log(f"❌ FAIL: Could not connect to Auto-Research service: {e}")
    
    # Test if code runner service is accessible
    try:
        response = requests.get("http://localhost:7072/health", timeout=5)
        if response.status_code == 200:
            log("✅ PASS: Code Runner service is accessible")
        else:
            log(f"❌ FAIL: Code Runner service returned status {response.status_code}")
    except requests.exceptions.RequestException as e:
        log(f"❌ FAIL: Could not connect to Code Runner service: {e}")
    
    # Test if postman service is accessible
    try:
        response = requests.get("http://localhost:7073/health", timeout=5)
        if response.status_code == 200:
            log("✅ PASS: Postman service is accessible")
        else:
            log(f"❌ FAIL: Postman service returned status {response.status_code}")
    except requests.exceptions.RequestException as e:
        log(f"❌ FAIL: Could not connect to Postman service: {e}")

def authenticate():
    """Authenticate with the LMS API"""
    log("=== Authenticating with LMS API ===")
    
    auth_url = f"{LMS_API_BASE_URL}/login"
    auth_data = {
        "request": {
            "apiKey": API_KEY,
            "secretKey": SECRET_KEY
        }
    }
    
    try:
        response = requests.post(auth_url, json=auth_data, timeout=10)
        if response.status_code == 200:
            token_data = response.json()
            if token_data.get("result"):
                token = token_data.get("token", "")
                log(f"✅ PASS: Authentication successful, token received: {token[:20]}...")
                return token
            else:
                log("❌ FAIL: Authentication failed - no token in response")
                log(f"Response: {json.dumps(token_data, indent=2)}")
        else:
            log(f"❌ FAIL: Authentication failed with status {response.status_code}")
            log(f"Response: {response.text}")
    except requests.exceptions.RequestException as e:
        log(f"❌ FAIL: Authentication request failed: {e}")
    
    return None

def test_account_search(token):
    """Test account search endpoint"""
    log("=== Testing Account Search ===")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    search_url = f"{LMS_API_BASE_URL}/account/search"
    search_data = {
        "accountAccountNumber": "123456789"
    }
    
    try:
        response = requests.post(search_url, json=search_data, headers=headers, timeout=10)
        if response.status_code == 200:
            accounts = response.json()
            log(f"✅ PASS: Account search successful, found {len(accounts)} accounts")
            
            # Verify response schema
            if accounts and len(accounts) > 0:
                account = accounts[0]
                required_fields = ["internalAccountIdentifier", "accountNumber", "accountStatus", "balance"]
                missing_fields = []
                
                for field in required_fields:
                    if field not in account:
                        missing_fields.append(field)
                
                if not missing_fields:
                    log("✅ PASS: Response data matches expected LMS schema")
                else:
                    log(f"⚠️  WARNING: Response missing required fields: {', '.join(missing_fields)}")
        else:
            log(f"❌ FAIL: Account search failed with status {response.status_code}")
            log(f"Response: {response.text}")
    except requests.exceptions.RequestException as e:
        log(f"❌ FAIL: Account search request failed: {e}")

def test_account_details(token, account_id):
    """Test account details endpoint"""
    log("=== Testing Account Details ===")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    details_url = f"{LMS_API_BASE_URL}/account/{account_id}"
    
    try:
        response = requests.get(details_url, headers=headers, timeout=10)
        if response.status_code == 200:
            account = response.json()
            log(f"✅ PASS: Account details retrieved successfully")
            
            # Verify response schema
            required_fields = ["internalAccountIdentifier", "accountNumber", "accountStatus", "balance", "persons"]
            missing_fields = []
            
            for field in required_fields:
                if field not in account:
                    missing_fields.append(field)
            
            if not missing_fields:
                log("✅ PASS: Response data matches expected LMS schema")
            else:
                log(f"⚠️  WARNING: Response missing required fields: {', '.join(missing_fields)}")
        else:
            log(f"❌ FAIL: Account details failed with status {response.status_code}")
            log(f"Response: {response.text}")
    except requests.exceptions.RequestException as e:
        log(f"❌ FAIL: Account details request failed: {e}")

def main():
    """Main execution function"""
    log("Starting LMS API Integration Demo")
    
    # Check environment variables
    if not os.getenv("OPENAI_API_KEY"):
        log("⚠️  WARNING: OPENAI_API_KEY not set in environment")
    if not os.getenv("VENICE_API_KEY"):
        log("⚠️  WARNING: VENICE_API_KEY not set in environment")
    
    # Test MCP service connections
    test_connection()
    
    # Authenticate with LMS API
    token = authenticate()
    if not token:
        log("❌ FAIL: Could not authenticate with LMS API - aborting tests")
        return 1
    
    # Test API endpoints
    test_account_search(token)
    
    # For account details, we need an account ID first
    # Let's search for an account to get an ID
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    search_url = f"{LMS_API_BASE_URL}/account/search"
    search_data = {
        "accountAccountNumber": "123456789"
    }
    
    try:
        response = requests.post(search_url, json=search_data, headers=headers, timeout=10)
        if response.status_code == 200:
            accounts = response.json()
            if accounts and len(accounts) > 0:
                account_id = accounts[0].get("internalAccountIdentifier", "")
                if account_id:
                    test_account_details(token, account_id)
                else:
                    log("⚠️  WARNING: No accounts found in search results")
            else:
                log("❌ FAIL: No accounts found in search results")
        else:
            log(f"❌ FAIL: Account search failed with status {response.status_code}")
    except requests.exceptions.RequestException as e:
        log(f"❌ FAIL: Account search request failed: {e}")
    
    log("LMS API Integration Demo completed")
    return 0

if __name__ == "__main__":
    sys.exit(main())