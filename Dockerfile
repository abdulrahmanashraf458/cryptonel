# Build stage
FROM python:3.11.8-alpine3.19 AS builder

# Install build dependencies
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    python3-dev \
    openblas-dev \
    lapack-dev \
    g++ \
    gfortran

# Set up virtual environment
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir wheel && \
    pip install --no-cache-dir -r requirements.txt

# Final stage
FROM alpine:3.19

# Install only runtime dependencies
RUN apk update && apk upgrade && \
    apk add --no-cache python3 libstdc++ openblas && \
    ln -sf python3 /usr/bin/python

# Copy Python packages from builder
COPY --from=builder /venv /venv
ENV PATH="/venv/bin:$PATH"

WORKDIR /app

# Copy application
COPY ddos/ ./ddos/
COPY setup.py README.md ./

# Create config
RUN mkdir -p /app/config /app/data /app/logs && \
    python -c "from ddos.config import Config; config = Config(); config.save('/app/config/ddos.yaml')"

# Security hardening
RUN addgroup -S appgroup && \
    adduser -S appuser -G appgroup && \
    chown -R appuser:appgroup /app && \
    chmod -R 755 /app

# Set security-related environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DDOS_CONFIG_PATH=/app/config/ddos.yaml \
    DDOS_DATA_DIR=/app/data

# Use non-root user
USER appuser

EXPOSE 8080 9090

CMD ["python", "-m", "ddos.manager", "--host", "0.0.0.0", "--port", "8080"] 