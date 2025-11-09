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
    
    # Check if catalog file exists
    catalog_path = '/app/mcp_catalog_multi.yaml'
    if not os.path.exists(catalog_path):
        logger.error(f"Catalog file not found at {catalog_path}")
        sys.exit(1)
    
    logger.info(f"Using catalog file: {catalog_path}")
    
    # Validate required environment variables
    required_vars = ['POSTMAN_API_KEY']
    for var in required_vars:
        if not os.getenv(var):
            logger.error(f"Required environment variable {var} not set")
            sys.exit(1)
    
    # Start the actual mcp-gateway service
    try:
        cmd = ['mcp-gateway', '--catalog', catalog_path, '--port', '2091']
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