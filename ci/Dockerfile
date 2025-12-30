# ci/Dockerfile
# Base image for jl-lseg-toolkit CI testing
# Contains Python 3.13, uv, and pre-cached wheels for fast installs
#
# Build and push using: ./ci/build-image.sh --push
# Or manually: docker build -t jlipworth/jl-lseg-toolkit-ci:latest -f ci/Dockerfile .

FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Pre-cache all dependency wheels (but don't create a venv)
# This populates /root/.cache/uv so `uv sync` is fast
WORKDIR /tmp/cache-build
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project && rm -rf .venv

# Clean up temp dir
WORKDIR /
RUN rm -rf /tmp/cache-build

# Default command
CMD ["bash"]
