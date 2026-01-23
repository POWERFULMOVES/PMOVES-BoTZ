# PMOVES MCP Bridge - Exposes PMOVES.AI infrastructure as MCP tools
# Build: docker build -t pmoves-mcp-bridge .
# Run: docker run -p 8100:8100 pmoves-mcp-bridge

FROM python:3.11-slim

LABEL org.opencontainers.image.title="PMOVES MCP Bridge"
LABEL org.opencontainers.image.description="MCP server exposing PMOVES.AI infrastructure services"
LABEL org.opencontainers.image.version="0.1.0"

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir httpx nats-py aiohttp

# Copy application
COPY . /app/

# Create non-root user
RUN useradd --create-home --shell /bin/bash pmoves && \
    chown -R pmoves:pmoves /app
USER pmoves

# Environment defaults
ENV PORT=8100
ENV HOST=0.0.0.0
ENV TENSORZERO_URL=http://tensorzero:3030
ENV HIRAG_URL=http://hi-rag-gateway-v2:8086
ENV NATS_URL=nats://nats:4222
ENV SUPABASE_URL=http://supabase:3010

EXPOSE 8100

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -sf http://localhost:8100/healthz || exit 1

# Run HTTP server mode
CMD ["python", "-m", "server", "--http", "--port", "8100"]
