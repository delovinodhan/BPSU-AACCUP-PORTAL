FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /data/uploads
ENV BPSU_PORTAL_DATA_DIR=/data BPSU_SECURE_COOKIE=1
EXPOSE 8080
CMD ["sh", "-c", "gunicorn --workers 1 --threads 8 --worker-class gthread --timeout 120 --bind 0.0.0.0:${PORT:-8080} app:app"]
