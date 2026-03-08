# ─── Build Stage ─────────────────────────────────────────────
FROM python:3.12-slim

LABEL maintainer="Banco Ágil" \
      description="Frontend Streamlit — demo e prototipação rápida"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY .streamlit/ .streamlit/
COPY static/ static/
COPY app.py .

RUN adduser --disabled-password --gecos "" --no-create-home appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
