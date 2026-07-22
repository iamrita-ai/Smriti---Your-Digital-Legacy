FROM python:3.11-slim

WORKDIR /app

# ca-certificates is REQUIRED for TLS handshakes to MongoDB Atlas to succeed
# inside this slim image - without it you get SSL handshake failures.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render's Web Service injects $PORT at runtime; we read it in config.py
EXPOSE 8080

CMD ["python", "main.py"]
