# 构建阶段
FROM python:3.11-slim as builder

WORKDIR /app

# Add build arguments for proxy
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

# Set proxy environment variables for the build
ENV HTTP_PROXY=$HTTP_PROXY
ENV HTTPS_PROXY=$HTTPS_PROXY
ENV NO_PROXY=$NO_PROXY

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
RUN pip install --no-cache-dir \
    celery \
    aio-pika \
    playwright \
    asyncio \
    aiohttp \
    psycopg2-binary \
    python-dotenv

# 运行阶段
FROM python:3.11-slim

WORKDIR /app

# 从构建阶段复制Python环境
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# 安装运行时必需的系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/* \
    && playwright install chromium \
    && playwright install-deps chromium

# 复制应用代码
COPY . .

# 设置健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 设置运行命令
CMD ["python", "-m", "app.main"] 