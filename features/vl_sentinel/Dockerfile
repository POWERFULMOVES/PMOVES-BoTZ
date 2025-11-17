FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app_vl.py ./
EXPOSE 7072
CMD ["uvicorn","app_vl:app","--host","0.0.0.0","--port","7072"]