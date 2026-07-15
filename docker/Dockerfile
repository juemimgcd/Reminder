ARG PYTHON_VERSION=3.12
FROM node:20-bookworm-slim AS frontend-builder

WORKDIR /frontend

COPY app/mneme_frontend_v0.2.1/package.json app/mneme_frontend_v0.2.1/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY app/mneme_frontend_v0.2.1/ ./
RUN npm run build

FROM python:${PYTHON_VERSION}-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    APP_PORT=8000 \
    UVICORN_WORKERS=1 \
    CELERY_WORKER_CONCURRENCY=1 \
    CELERY_LOG_LEVEL=INFO \
    WAIT_FOR_TIMEOUT_SECONDS=180 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    HF_ENDPOINT=https://hf-mirror.com

WORKDIR /app

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_EXTRA_INDEX_URL=

COPY requirements.txt ./
COPY requirements/ ./requirements/

RUN python -m pip install --upgrade pip setuptools wheel && \
    if [ -n "$PIP_EXTRA_INDEX_URL" ]; then \
        python -m pip install \
        --retries 10 \
        --timeout 120 \
        --prefer-binary \
        --no-compile \
        --index-url "$PIP_INDEX_URL" \
        --extra-index-url "$PIP_EXTRA_INDEX_URL" \
        -r requirements.txt; \
    else \
        python -m pip install \
        --retries 10 \
        --timeout 120 \
        --prefer-binary \
        --no-compile \
        --index-url "$PIP_INDEX_URL" \
        -r requirements.txt; \
    fi

COPY . .
COPY --from=frontend-builder /frontend/dist /app/app/mneme_frontend_v0.2.1/dist

RUN test -d /app/services/memory_agent && \
    test -f /app/docker/start-memory-agent-api.sh && \
    test -f /app/docker/start-memory-agent-worker.sh

EXPOSE 8000 8010

CMD ["sh", "/app/docker/start-api.sh"]
