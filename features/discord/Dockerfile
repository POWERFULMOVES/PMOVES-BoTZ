FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY bot.py ./
RUN adduser -D -u 1000 appuser && chown -R appuser:appuser /app
USER appuser
ENV SHIM_BASE=http://localhost:7069
CMD ["python","bot.py"]