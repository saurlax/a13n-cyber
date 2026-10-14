ARG PYTHON_BASE_IMAGE=python:3.13-slim-bookworm
FROM ${PYTHON_BASE_IMAGE}
COPY --from=ghcr.io/astral-sh/uv:0.9.16 /uv /bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_PYTHON_DOWNLOADS=0 \
    UV_CONCURRENT_DOWNLOADS=4 UV_HTTP_TIMEOUT=30 UV_HTTP_RETRIES=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/
COPY agents/ ./agents/
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-editable
ENV PATH="/app/.venv/bin:$PATH"
ENTRYPOINT ["a13n-cyber"]
CMD ["tsecbench"]
