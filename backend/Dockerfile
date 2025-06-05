FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for soundfile and torch
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv using the official installation script
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies using uv
RUN uv pip sync requirements.txt

# Copy the rest of the application
COPY . .

# Create directory for audio files
RUN mkdir -p audio_files

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "calling_model:app", "--host", "0.0.0.0", "--port", "8000"] 