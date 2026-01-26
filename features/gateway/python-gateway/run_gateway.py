#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import logging
import signal

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting MCP Gateway...")

    # Gateway uses hardcoded upstream servers in gateway.py
    # No external catalog file is required
    logger.info("Using built-in MCP upstream server configuration")
    
    # Start the actual mcp-gateway service
    try:
        cmd = ['/app/venv/bin/python', '/app/gateway.py']
        logger.info(f"Running command: {' '.join(cmd)}")
        
        # Set up signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            sys.exit(0)
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # Run the gateway with proper error handling
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        # Stream output
        for line in iter(process.stdout.readline, ''):
            if line:
                logger.info(line.rstrip())
            
        process.wait()
        return process.returncode
        
    except FileNotFoundError:
        logger.error("mcp-gateway command not found")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error starting gateway: {e}")
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())