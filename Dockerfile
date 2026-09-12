FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend:/app \
    NEXORA_DATA_DIR=/app/data

WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY frontend /app/frontend
COPY agents /app/agents
COPY README.md ARCHITECTURE.md AGENT_CONFIGURATION.md /app/

RUN mkdir -p /app/data

WORKDIR /app/backend
EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --timeout-keep-alive ${UVICORN_KEEP_ALIVE:-15} --timeout-graceful-shutdown ${UVICORN_GRACEFUL_SHUTDOWN:-30}"]
