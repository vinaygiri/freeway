# Freeway proxy (free-claude-code) — local/self-host image.
# Multi-stage: uv resolves deps into a venv, the runtime layer just copies it.
# Patch pinned to match proxy/.python-version (uv honors it on sync).
FROM python:3.14.0-slim AS builder

# uv binary from the official distroless image (pinned major line).
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# Dependency layer first (cached until pyproject/lock change) — runtime deps only.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Application source, then install the project itself into the same venv.
COPY . .
RUN uv sync --frozen --no-dev


FROM python:3.14.0-slim AS runtime

# Non-root runtime user with a writable home for the app's ~/.fcc config + logs.
RUN groupadd --system freeway \
    && useradd --system --gid freeway --home-dir /home/freeway --create-home freeway

WORKDIR /app

# Bring the resolved venv + source from the builder.
COPY --from=builder --chown=freeway:freeway /app /app

ENV PATH="/app/.venv/bin:${PATH}" \
    HOME=/home/freeway \
    FCC_HOST=0.0.0.0 \
    FCC_PORT=8082 \
    PYTHONUNBUFFERED=1

USER freeway

EXPOSE 8082

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8082/health', timeout=2).status==200 else 1)" || exit 1

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8082", "--timeout-graceful-shutdown", "5"]
