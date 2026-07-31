FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
    PIP_TRUSTED_HOST=mirrors.aliyun.com \
    UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
    PYTHONPATH=/app/backend

RUN pip install --no-cache-dir uv && useradd -m appuser

WORKDIR /app

COPY pyproject.toml README.md ./
COPY backend ./backend
COPY scripts ./scripts

RUN uv pip install --system -e . \
    && chmod +x backend/entrypoint.sh \
    && chown -R appuser /app

USER appuser

EXPOSE 8000

CMD ["./backend/entrypoint.sh"]
