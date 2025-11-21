#!/bin/sh
set -e

echo "Starting Tailscale container..."

# Create TUN device if it doesn't exist
mkdir -p /dev/net
if [ ! -e /dev/net/tun ]; then
  echo "Creating TUN device..."
  mknod /dev/net/tun c 10 200 || echo "Warning: Failed to create TUN device, may already exist"
fi

# Start tailscaled daemon
echo "Starting tailscaled daemon..."
tailscaled --state=/var/lib/tailscale/tailscaled.state --socket=/var/run/tailscale/tailscaled.sock --tun=userspace-networking &
TAILSCALED_PID=$!

# Wait for tailscaled to start
sleep 5

# Check if tailscaled is running
if ! kill -0 $TAILSCALED_PID 2>/dev/null; then
  echo "Error: tailscaled failed to start"
  exit 1
fi

# Connect to Tailscale if auth key is provided
if [ -n "${TS_AUTHKEY}" ]; then
  echo "Connecting to Tailscale with provided auth key..."
  tailscale up --authkey=${TS_AUTHKEY} --reset --accept-routes=true --ssh=true || echo "Warning: Failed to connect to Tailscale"
else
  echo "No auth key provided, starting in unauthenticated mode..."
fi

# Keep container running
echo "Tailscale setup complete. Keeping container running..."
tail -f /dev/null