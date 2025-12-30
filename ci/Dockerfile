# ci/Dockerfile
# Base image for jl-lseg-toolkit CI testing
# Contains Python 3.12, uv, and project dependencies pre-installed
#
# Build and push using: ./ci/build-image.sh --push
# Or manually: docker build -t jlipworth/jl-lseg-toolkit-ci:latest -f ci/Dockerfile .

FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files first (for caching)
COPY pyproject.toml uv.lock ./

# Install dependencies (cached layer) - dev dependencies included for testing
RUN uv sync --frozen --no-install-project

# Default command
CMD ["bash"]
