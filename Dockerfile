# ShadowNet C2 Server
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies (needed for bcrypt/cryptography wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a venv
COPY server/requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# ============================
# Runtime stage
# ============================
FROM python:3.11-slim

WORKDIR /app/server

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Runtime system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 curl \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY server/ /app/server/
COPY agent/agent.env /app/agent/agent.env

# Create data directory for database (ephemeral on free tier, persists on paid)
RUN mkdir -p /app/data

# Python env
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/server

# DB path default (can be overridden by env var)
ENV SHADOWNET_DB_PATH=/app/data/shadownet.db

# Render injects $PORT at runtime — DO NOT hardcode a port number.
# Flask reads PORT in __main__. We expose a placeholder; Render ignores EXPOSE anyway.
EXPOSE 10000

# Run flask directly
CMD python server_with_event.py
