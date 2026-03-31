FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System dependencies for OpenCV, PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install email-validator bcrypt==4.2.1

# Copy backend code
COPY backend/ .

# Create directories
RUN mkdir -p uploads logs ai/weights

# Expose port (Railway sets PORT env var)
EXPOSE 8000

# Start command -- Railway provides PORT
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
