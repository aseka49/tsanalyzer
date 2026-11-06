# Multi-stage image for tsanalyzer.
#   docker build --target test    -t tsanalyzer-test .   # tools + tests, used by CI
#   docker build --target runtime -t tsanalyzer .        # small production image (default)
#
# The runtime image starts the HTTP API on port 8000. The command-line tool is also inside:
#   docker run --rm --entrypoint tsanalyzer tsanalyzer examples/temperature.csv --value-col temp_c

ARG PYTHON_IMAGE=python:3.12-slim

# ---------- base: shared settings ----------
FROM ${PYTHON_IMAGE} AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MPLBACKEND=Agg
WORKDIR /app

# ---------- test: dev dependencies, sources and tests ----------
FROM base AS test
# Copy only the metadata first so the dependency layer is cached between commits.
COPY pyproject.toml README.md ./
COPY src/tsanalyzer/__init__.py src/tsanalyzer/__init__.py
RUN pip install ".[dev]"
COPY src ./src
COPY tests ./tests
COPY examples ./examples
RUN pip install --no-deps -e . && mkdir -p /app/reports
CMD ["pytest", "--cov", "--cov-report=term-missing", "--cov-report=xml:reports/coverage.xml", "--junitxml=reports/junit.xml"]

# ---------- build: produce a wheel ----------
FROM base AS build
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip wheel --no-deps --wheel-dir /dist .

# ---------- runtime: minimal image that runs the service ----------
FROM base AS runtime
ARG VERSION=dev
ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="tsanalyzer" \
      org.opencontainers.image.description="Cleaning, statistics and trend analysis for scientific time series" \
      org.opencontainers.image.source="https://github.com/aseka49/tsanalyzer" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}"

COPY --from=build /dist /tmp/dist
RUN pip install /tmp/dist/*.whl && rm -rf /tmp/dist \
    && useradd --create-home --uid 10001 app
COPY examples ./examples

USER app
ENV TSANALYZER_HOST=0.0.0.0 TSANALYZER_PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
CMD ["tsanalyzer-server"]
