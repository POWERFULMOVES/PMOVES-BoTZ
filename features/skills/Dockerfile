FROM python:3.11-slim

# Create non-root user
RUN useradd -r -u 1001 -s /usr/sbin/nologin skills

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy skill server and all skill sources
COPY skill_server.py .
COPY library/ ./library/
COPY repos/ ./repos/

# Ensure non-root user owns app files
RUN chown -R skills:skills /app

# Run as non-root user
USER skills

# Run skill server
CMD ["python", "skill_server.py", "--transport", "stdio"]
