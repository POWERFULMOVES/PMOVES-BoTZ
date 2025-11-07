FROM python:3.11-slim
RUN pip install --no-cache-dir pipx && pipx ensurepath &&     apt-get update && apt-get install -y --no-install-recommends bash curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app_crush.py ./
EXPOSE 7069
CMD ["python","app_crush.py"]