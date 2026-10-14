ARG PYTHON_BASE_IMAGE=python:3.12-slim-bookworm
FROM ${PYTHON_BASE_IMAGE}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/src
WORKDIR /app
COPY src/ ./src/
# Preparation image: no third-party runtime dependencies or embedded secrets.
# Add solver tools at build time once the challenge requirements are verified.
ENTRYPOINT ["python", "-m", "tsec_agent"]
CMD ["doctor"]
