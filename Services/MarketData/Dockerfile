# Build context: services/market-data
FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim
RUN useradd --create-home --uid 10001 appuser
WORKDIR /srv
COPY --from=builder /install /usr/local
# COPY alembic.ini ./
# COPY migrations ./migrations
# COPY config ./config
USER appuser
EXPOSE 8001
# HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=5 \
#   CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health/live')"
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8001"] 
# alembic upgrade head && 
