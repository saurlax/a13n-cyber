ARG PYTHON_BASE_IMAGE=python:3.13-slim-bookworm
FROM ${PYTHON_BASE_IMAGE}
COPY --from=ghcr.io/astral-sh/uv:0.9.16 /uv /bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_PYTHON_DOWNLOADS=0 \
    UV_CONCURRENT_DOWNLOADS=4 UV_HTTP_TIMEOUT=30 UV_HTTP_RETRIES=1 UV_LINK_MODE=copy \
    TERM=dumb PWNLIB_NOTERM=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash binutils build-essential ca-certificates curl ffuf file gdb git jq \
        libffi-dev libssl-dev netcat-openbsd nmap openssl ripgrep tar unzip xxd zip \
    && mkdir -p /usr/local/share/a13n-cyber \
    && dpkg-query -W > /usr/local/share/a13n-cyber/system-packages.tsv \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/
COPY agents/ ./agents/
COPY scripts/check-image.py ./scripts/check-image.py
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-editable --extra toolkit
ENV PATH="/app/.venv/bin:$PATH"
ENTRYPOINT ["a13n-cyber"]
CMD ["--help"]
