FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip/setuptools first, then install dependencies directly
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir \
        fastapi==0.111.0 \
        "uvicorn[standard]==0.30.1" \
        starlette==0.37.2 \
        python-multipart==0.0.9 \
        "sqlalchemy[asyncio]==2.0.30" \
        asyncpg==0.29.0 \
        alembic==1.13.1 \
        "redis[hiredis]==5.0.4" \
        "celery[redis]==5.4.0" \
        kombu==5.3.7 \
        "python-jose[cryptography]==3.3.0" \
        "passlib[bcrypt]==1.7.4" \
        bcrypt==4.0.1 \
        cryptography==42.0.7 \
        pydantic==2.7.1 \
        pydantic-settings==2.2.1 \
        email-validator==2.1.1 \
        httpx==0.27.0 \
        python-dateutil==2.9.0 \
        pytz==2024.1 \
        aiofiles==23.2.1 \
        orjson==3.10.3 \
        Pillow==10.3.0 \
        reportlab==4.1.0 \
        openpyxl==3.1.2 \
        pandas==2.2.2 \
        aiosmtplib==3.0.1 \
        jinja2==3.1.4 \
        structlog==24.2.0

# Copy application source
COPY . .

# Create non-root user
RUN useradd -m -u 1000 uem && \
    mkdir -p /app/pki/ca /app/packages /app/logs && \
    chown -R uem:uem /app

USER uem

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
