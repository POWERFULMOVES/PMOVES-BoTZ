#!/bin/sh
echo "Starting Tailscale..."

# Create TUN device if needed
mkdir -p /dev/net
if [ ! -e /dev/net/tun ]; then
  mknod /dev/net/tun c 10 200
fi

# Start tailscaled
tailscaled --state=/var/lib/tailscale/tailscaled.state &
sleep 5

# Connect to Tailscale
tailscale up --authkey=${TAILSCALE_AUTHKEY} --reset --accept-routes=true --ssh=true

# Keep container running
tail -f /dev/null