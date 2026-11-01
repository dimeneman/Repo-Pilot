# syntax=docker/dockerfile:1
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies for git, build-essential, and SSL
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Pre-install CPU-only PyTorch first to prevent downloading ~2.5GB of CUDA wheels,
# avoiding PyPI read timeouts and drastically reducing image build time and size.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --user --default-timeout=120 --retries 5 \
        torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir --user --default-timeout=120 --retries 5 \
        -r requirements.txt

# Final runtime image
FROM python:3.12-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/root/.local/lib/python3.12/site-packages:$PYTHONPATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy application source code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

