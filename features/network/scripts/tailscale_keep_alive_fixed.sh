#!/bin/sh
# Simple script to keep Tailscale container running
echo "Starting Tailscale keep-alive script..."

# Create TUN device if it doesn't exist
mkdir -p /dev/net
if [ ! -e /dev/net/tun ]; then
  mknod /dev/net/tun c 10 200
fi

# Start tailscaled with userspace networking
tailscaled --state=/var/lib/tailscale/tailscaled.state --socket=/var/run/tailscale/tailscaled.sock --tun=userspace-networking &
sleep 5

# Connect to Tailscale
tailscale up --authkey=${TAILSCALE_AUTHKEY} --reset --accept-routes=true --ssh=true

# Keep container running
tail -f /dev/null