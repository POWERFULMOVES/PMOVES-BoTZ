FROM alpine:3.20

# Install system dependencies
RUN apk add --no-cache bash curl python3 py3-pip pipx

# Install mcp-server, mcp, and mcp-gateway using pipx
RUN pipx install mcp-server && pipx install mcp[cli] && pipx install mcp-gateway==1.1.0

# Ensure pipx binaries are in PATH
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy scripts to run the gateway and test connections
COPY run_gateway.py .
COPY test_connection.py .

# Install requests for testing
RUN pip install --break-system-packages requests

# Expose the port
EXPOSE 2091

# Run the mcp gateway using Python script
CMD ["python", "run_gateway.py"]