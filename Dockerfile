FROM ghcr.io/astral-sh/uv:python3.12-bookworm

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Install system dependencies including libpq and curl (for container health probes)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*
    
WORKDIR /app

# Pre-cache the application dependencies.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync  --no-install-project

# Copy the application into the container.
COPY . /app

# Install the application dependencies.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync 

EXPOSE 8000

# Run the application.
# CMD ["uv", "run", "python", "server.py", "--host", "0.0.0.0", "--port", "8000"]

CMD [".venv/bin/python3.12", "python", "server.py", "--host", "0.0.0.0", "--port", "8000"]

##docker build . -t deer-flow-backend.prd:latest  --build-arg https_proxy=http://192.168.0.106:1087  --build-arg http_proxy=http://192.168.0.106:1087 --build-arg no_proxy=localhost,192.168.0.106,.local  

