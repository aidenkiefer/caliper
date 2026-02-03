FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt ./

# Install Python dependencies using pip (more reliable than Poetry in Docker)
RUN pip install --no-cache-dir -r requirements.txt

# Copy dependency metadata files (for package structure)
COPY pyproject.toml poetry.lock* ./
COPY services/api/pyproject.toml ./services/api/
COPY packages/common/pyproject.toml ./packages/common/

# Copy application code
COPY . .

# Keep working directory at repo root so "services.api" is a proper package
WORKDIR /app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/v1/health || exit 1

# Run uvicorn with module path so relative imports in main.py resolve (services.api.main:app)
CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
