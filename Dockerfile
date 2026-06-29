FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for C extensions (HDBSCAN / UMAP build requirements)
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Initialize SQLite DB
RUN python -c "from pulse.ledger.db import init_db; init_db()"

# Hugging Face Spaces default port is 7860
EXPOSE 7860

# Run Uvicorn on port 7860
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "7860"]
