ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120

WORKDIR /app

ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_EXTRA_INDEX_URL=

COPY requirements.txt ./

RUN python -m pip install --upgrade pip setuptools wheel && \
    if [ -n "$PIP_EXTRA_INDEX_URL" ]; then \
        python -m pip install \
        --retries 10 \
        --timeout 120 \
        --prefer-binary \
        --index-url "$PIP_INDEX_URL" \
        --extra-index-url "$PIP_EXTRA_INDEX_URL" \
        -r requirements.txt; \
    else \
        python -m pip install \
        --retries 10 \
        --timeout 120 \
        --prefer-binary \
        --index-url "$PIP_INDEX_URL" \
        -r requirements.txt; \
    fi

COPY . .

EXPOSE 8000

CMD ["/bin/sh", "-c", "alembic upgrade head && exec uvicorn main:app --host 0.0.0.0 --port 8000"]
