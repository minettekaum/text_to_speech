FROM python:3.11-slim

# Copy uv binary from the official distroless image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Install system dependencies required for soundfile and torch
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies with UV
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project

# Copy the backend folder into the container
COPY . .

# Sync the project dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Create directory for audio files
RUN mkdir -p audio_files

# Expose the application port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
