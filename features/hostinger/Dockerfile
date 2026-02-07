# Hostinger MCP Server
# Uses official hostinger-api-mcp npm package
FROM node:20-slim

WORKDIR /app

# Install hostinger-api-mcp globally
RUN npm install -g hostinger-api-mcp@latest

# Copy entrypoint
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Environment variables
ENV API_TOKEN=""

# MCP runs on stdio
ENTRYPOINT ["/app/entrypoint.sh"]
