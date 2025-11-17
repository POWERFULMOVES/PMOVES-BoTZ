FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app_e2b.py ./
EXPOSE 7071
CMD ["uvicorn","app_e2b:app","--host","0.0.0.0","--port","7071"]