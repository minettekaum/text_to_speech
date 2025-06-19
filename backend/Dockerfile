# Build stage
FROM python:3.11-slim as builder

# Copy uv binary from the official distroless image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project

# Copy the project into the image
COPY . .

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Production stage
FROM python:3.11-slim

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy application code
COPY main.py utils.py ./

# Create directory for audio files and uploads
RUN mkdir -p audio_files upload_files

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["python", "-m", "fastapi", "run", "main.py", "--port", "8000", "--host", "0.0.0.0"]