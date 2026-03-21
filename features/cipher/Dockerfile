FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app_memory.py .

# Create non-root user and data directory
RUN useradd -r -u 1001 -s /usr/sbin/nologin cipher \
    && mkdir -p /data \
    && chown cipher:cipher /data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV MCP_MEMORY_DB_PATH=/data/memory.db

# Expose port for MCP server
EXPOSE 3025

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sqlite3; sqlite3.connect('/data/memory.db').close()" || exit 1

# Run as non-root user
USER cipher

# Run the MCP server
CMD ["python", "app_memory.py"]