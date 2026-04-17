# Hostinger MCP Server
# Uses official hostinger-api-mcp npm package
FROM node:20-slim

WORKDIR /app

# Install hostinger-api-mcp globally
RUN npm install -g hostinger-api-mcp@latest

# Copy entrypoint and fix line endings (Windows CRLF → Unix LF)
COPY entrypoint.sh /app/entrypoint.sh
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Use existing node user (UID 1000) from node:20-slim
RUN chown -R node:node /app
USER node

# Environment variables
ENV API_TOKEN=""

# MCP runs on stdio
ENTRYPOINT ["/app/entrypoint.sh"]
