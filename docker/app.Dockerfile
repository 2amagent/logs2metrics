FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

RUN groupadd -g 1000 appuser && useradd -u 1000 -g appuser -m appuser

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev

COPY drain3.ini ./
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN chown -R appuser:appuser /app

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
# Run uvicorn directly from the synced venv rather than via `uv run`, which
# would try to write its cache dir on every startup — unnecessary at runtime
# and a permission error under a non-root, read-mostly container filesystem.
CMD ["/app/.venv/bin/uvicorn", "logtriage.main:app", "--host", "0.0.0.0", "--port", "8000"]
