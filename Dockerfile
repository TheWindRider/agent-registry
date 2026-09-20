FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

# Copy application code
COPY registry_server.py registry_store.py ./

# Cloud Run injects $PORT (default 8080 locally)
ENV PORT=8080
EXPOSE 8080

# FastAPI (ASGI) served by gunicorn with uvicorn workers
CMD ["sh", "-c", "exec gunicorn -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:${PORT} registry_server:app"]
