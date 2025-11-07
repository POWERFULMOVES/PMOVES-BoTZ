FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY bot.py ./
ENV SHIM_BASE=http://localhost:7069
CMD ["python","bot.py"]