FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for Docker cache)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY . .

# Install BITTU
RUN pip install --no-cache-dir -e .

# Make scripts executable
RUN chmod +x *.sh

# Expose port (if needed for web interface)
EXPOSE 8080

# Default command
CMD ["bittu", "--plain"]
