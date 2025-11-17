#!/usr/bin/env python3
"""
Simple keep-alive script for Cipher Memory container
"""
import time
import sys
import os

def main():
    print("Starting Cipher Memory keep-alive script...")
    print("This script keeps the container running for health checks.")
    
    # Create a simple database file for health check
    import sqlite3
    db_path = os.environ.get('MCP_MEMORY_DB_PATH', '/data/memory.db')
    try:
        conn = sqlite3.connect(db_path)
        conn.close()
        print(f"Database created/verified at {db_path}")
    except Exception as e:
        print(f"Database error: {e}")
    
    # Keep container alive
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Shutting down...")
        sys.exit(0)

if __name__ == "__main__":
    main()