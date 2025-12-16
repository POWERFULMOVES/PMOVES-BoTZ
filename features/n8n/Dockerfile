FROM python:3.11-slim

WORKDIR /app

# Install Node.js for cipher CLI integration
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app_n8n_agent.py .

# Health check placeholder
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "print('healthy')" || exit 1

# Run MCP server (stdio mode)
CMD ["python", "app_n8n_agent.py"]
