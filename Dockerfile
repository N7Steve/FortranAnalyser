# syntax=docker/dockerfile:1
FROM node:24-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM ghcr.io/astral-sh/uv:0.12.10 AS uv

FROM python:3.12-slim-bookworm AS backend
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE.txt ./
COPY backend/ ./backend/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra web --no-editable --python /usr/local/bin/python

FROM backend AS test
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --extra web --extra dev --no-editable --python /usr/local/bin/python
COPY tests/ ./tests/
RUN uv run --frozen --extra web --extra dev python -m pytest -q

FROM python:3.12-slim-bookworm AS runtime
LABEL org.opencontainers.image.title="FortranAnalyser" \
      org.opencontainers.image.description="Local Fortran analysis with a web interface" \
      org.opencontainers.image.source="https://github.com/N7Steve/FortranAnalyser" \
      org.opencontainers.image.licenses="GPL-3.0-or-later"
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    HOME=/tmp \
    FORTRAN_BIND_HOST=0.0.0.0 FORTRAN_PORT=8000 \
    FORTRAN_ALLOWED_HOSTS="*" \
    FORTRAN_FRONTEND_DIR=/app/frontend \
    FORTRAN_DATA_DIR=/data
WORKDIR /app
RUN groupadd --gid 568 analyser \
    && useradd --uid 568 --gid 568 --no-create-home --home-dir /tmp analyser \
    && mkdir /data && chown 568:568 /data
COPY --from=backend /app/.venv /app/.venv
COPY --from=frontend /build/frontend/dist /app/frontend
COPY LICENSE.txt /app/LICENSE.txt
USER 568:568
EXPOSE 8000
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["/app/.venv/bin/python", "-m", "fortran_analyser.healthcheck"]
ENTRYPOINT ["/app/.venv/bin/python", "-m", "fortran_analyser.web"]
