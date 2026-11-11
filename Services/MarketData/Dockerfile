# Build context: services/market-data
FROM python:3.12-slim-bookworm AS builder
WORKDIR /build
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim-bookworm
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb \
       -o /tmp/packages-microsoft-prod.deb \
    && dpkg -i /tmp/packages-microsoft-prod.deb \
    && rm /tmp/packages-microsoft-prod.deb \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 unixodbc \
    && apt-get purge -y --auto-remove curl gnupg \
    && rm -rf /var/lib/apt/lists/*
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
