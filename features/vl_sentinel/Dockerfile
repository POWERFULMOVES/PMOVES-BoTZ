FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app_vl.py ./
RUN adduser -D -u 1000 appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 7072
CMD ["uvicorn","app_vl:app","--host","0.0.0.0","--port","7072"]