FROM python:3.12-slim

# Python runtime configuration
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    FRAPPE_MCP_MODE=production \
    FRAPPE_BASE_URL=http://frappe:8000 \
    PORT=8800

WORKDIR /app

# Install Python dependencies first for better Docker layer caching
COPY requirements.txt .

RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

# Copy MCP application source
COPY run.py .
COPY mcpp ./mcpp

EXPOSE 8800

CMD ["python", "run.py", "--http", "--mode", "production", "--port", "8800"]