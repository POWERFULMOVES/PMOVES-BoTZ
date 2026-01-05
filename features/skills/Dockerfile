FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy skill server and all skill sources
COPY skill_server.py .
COPY library/ ./library/
COPY repos/ ./repos/

# Run skill server
CMD ["python", "skill_server.py", "--transport", "stdio"]
