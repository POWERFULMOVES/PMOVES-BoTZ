#!/bin/bash

# Smoke test for PMOVES yt-mini agent

echo "Starting yt-mini smoke test..."

# Ensure the service is up (assuming base.yml is running or we start it)
# For this test, we'll try to exec into the container. If it fails, we'll try to start it.

CONTAINER_NAME="yt-mini"

if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
    echo "Container $CONTAINER_NAME is running."
else
    echo "Container $CONTAINER_NAME is not running. Attempting to start..."
    # Try starting using the feature compose file if base isn't up, or just fail if expected to be part of base
    # But since we integrated into base, we should probably assume the user starts the stack.
    # However, for a standalone test, let's try to use the feature compose.
    docker compose -f features/yt/docker-compose.yml up -d --build
fi

echo "Running 'status' command..."
docker exec $CONTAINER_NAME python cli.py status

if [ $? -eq 0 ]; then
    echo "Status check PASSED."
else
    echo "Status check FAILED."
    exit 1
fi

echo "Running 'analyze' mock command..."
docker exec $CONTAINER_NAME python cli.py analyze "PL12345"

if [ $? -eq 0 ]; then
    echo "Analyze mock check PASSED."
else
    echo "Analyze mock check FAILED."
    exit 1
fi

echo "yt-mini smoke test COMPLETE."
