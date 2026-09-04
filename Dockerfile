# Dockerfile for REMAININGCONNECTIONS
# Build image: docker build -t rc-app .
# Run dashboard generator: docker run --rm -v $(pwd)/data:/app/data -v $(pwd)/docs:/app/docs rc-app scripts/dashboard_generator.py
# Run API server: docker run --rm -p 8080:8080 -v $(pwd)/data:/app/data rc-app scripts/api_server.py

FROM python:3.11-slim

LABEL maintainer="B3B3097"
LABEL description="Automated Proxy Discovery & Dashboard System"
LABEL version="1.0"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOME=/app

WORKDIR $APP_HOME

# Install system dependencies for building some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY . .

# Create directories for data persistence
RUN mkdir -p $APP_HOME/data $APP_HOME/docs

# Expose port for API server (optional)
EXPOSE 8080

# Default command (can be overridden)
CMD ["python", "scripts/dashboard_generator.py"]