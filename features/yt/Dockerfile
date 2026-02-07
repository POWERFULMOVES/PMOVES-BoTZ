FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create non-root user
RUN adduser -D -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Default command to keep container running for exec, or run the CLI
CMD ["tail", "-f", "/dev/null"]
