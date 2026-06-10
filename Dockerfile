FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --retries=5 --start-period=30s \
    CMD python -c "import json, urllib.request; r=urllib.request.urlopen('http://localhost:8000/health', timeout=5); raise SystemExit(0 if r.status == 200 else 1)"

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
