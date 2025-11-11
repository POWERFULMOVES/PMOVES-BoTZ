#!/bin/sh
echo "Starting Tailscale..."

# Create TUN device if needed
mkdir -p /dev/net
if [ ! -e /dev/net/tun ]; then
  echo "Creating TUN device"
  mknod /dev/net/tun c 10 200 || echo "Failed to create TUN device"
fi

# Start tailscaled
echo "Starting tailscaled daemon..."
tailscaled --state=/var/lib/tailscale/tailscaled.state &
sleep 10

# Connect to Tailscale
echo "Connecting to Tailscale..."
tailscale up --authkey=${TAILSCALE_AUTHKEY} --reset --accept-routes=true --ssh=true || echo "Failed to connect to Tailscale"

# Keep container running
while true; do
  sleep 30
  # Check if tailscaled is still running
  if ! pgrep tailscaled > /dev/null; then
    echo "tailscaled process died, restarting..."
    tailscaled --state=/var/lib/tailscale/tailscaled.state &
    sleep 5
    tailscale up --authkey=${TAILSCALE_AUTHKEY} --reset --accept-routes=true --ssh=true
  fi
done
