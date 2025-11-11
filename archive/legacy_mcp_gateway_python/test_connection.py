#!/usr/bin/env python3
import requests
import json

def test_docling_connection():
    """Test if we can connect to docling service"""
    try:
        # Try to connect to docling service
        response = requests.get("http://127.0.0.1:3020", timeout=5)
        print(f"Docling service responded with status code: {response.status_code}")
        
        # Try to get MCP server info
        response = requests.get("http://127.0.0.1:3020/mcp", timeout=5)
        print(f"MCP endpoint responded with status code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"MCP server info: {json.dumps(data, indent=2)}")
            except json.JSONDecodeError:
                print(f"Response is not valid JSON: {response.text}")
        
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to docling service: {e}")
        return False

if __name__ == "__main__":
    print("Testing connection to docling service...")
    success = test_docling_connection()
    if success:
        print("Connection test successful!")
    else:
        print("Connection test failed!")