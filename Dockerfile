FROM python:3.12-slim AS base

LABEL maintainer="Banco Ágil" \
      description="API Backend do Banco Ágil"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

FROM base AS deps

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM deps AS app

COPY src/ ./src/
COPY data/ ./data/
COPY docs/ ./docs/
COPY server.py .
COPY pyproject.toml .

RUN mkdir -p /app/data && \
    adduser --disabled-password --gecos "" --no-create-home appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

ENTRYPOINT ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
