FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# 安装Playwright及其依赖
RUN pip install --no-cache-dir playwright && \
    playwright install chromium && \
    playwright install-deps chromium

# 安装Python依赖
RUN pip install --no-cache-dir \
    celery \
    aio-pika \
    playwright \
    asyncio \
    aiohttp \
    psycopg2-binary \
    python-dotenv

# 复制应用代码
COPY . .

# 设置健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Add build arguments for proxy
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

# Set proxy environment variables for the build
ENV HTTP_PROXY=$HTTP_PROXY
ENV HTTPS_PROXY=$HTTPS_PROXY
ENV NO_PROXY=$NO_PROXY

# 设置运行命令
CMD ["python", "-m", "app.main"] 