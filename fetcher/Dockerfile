# ---------- 构建阶段 ----------
FROM python:3.11-slim AS builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装依赖到临时目录
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install -r requirements.txt

# ---------- 运行阶段 ----------
FROM python:3.11-slim

WORKDIR /app

# 创建非 root 用户
RUN useradd -m appuser

# 拷贝依赖和代码
COPY --from=builder /install /usr/local
COPY . .

# 权限设置
RUN chown -R appuser:appuser /app

USER appuser

# 暴露 FastAPI 端口
EXPOSE 8000

# 默认启动命令（可被 docker-compose 覆盖）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]