FROM alpine:3.20

# Install system dependencies
RUN apk add --no-cache bash curl python3 py3-pip pipx

# Install uv for package management
RUN pip install --break-system-packages uv

# Install mcp-server, mcp using pipx, and fastmcp using pip
RUN pipx install mcp-server && pipx install mcp[cli] && python3 -m venv /app/venv && /app/venv/bin/pip install --break-system-packages fastmcp

# Ensure pipx binaries are in PATH
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy scripts to run the gateway and test connections
COPY run_gateway.py .
COPY test_connection.py .
COPY gateway.py .

# Install requests, PyYAML, and additional dependencies for health endpoint
RUN pip install --break-system-packages requests pyyaml fastapi uvicorn

# Expose the port
EXPOSE 2091

# Run the mcp gateway using Python script
CMD ["python", "run_gateway.py"]