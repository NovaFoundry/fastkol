

# Fetcher 服务启动指南

## 简介

Fetcher 是一个数据获取服务，集成了 FastAPI 和 Nacos，支持服务发现。本文档提供了详细的启动步骤和配置说明。

## 环境要求

- Python 3.8+
- Docker 和 Docker Compose
- 网络连接（用于服务注册和发现）

## 快速启动

### 1. 启动 Docker 环境

```bash
# 进入 Docker 环境目录
cd docker/environments/dev
docker compose up -d
```

### 2. 安装依赖

```bash
# 安装所有必要的依赖包
pip install -r requirements.txt
```

### 3. 启动 Api 服务

```bash

# 使用 uvicorn 启动服务(开发环境)
uvicorn app.main:app --host 0.0.0.0 --port 18102 --reload

# 使用 gunicorn 启动服务(生产环境)
gunicorn -w 4 -b 0.0.0.0:18102 app.main:app
```

### 4. 验证服务

- API 文档：`http://localhost:18102/docs`
- 健康检查：`http://localhost:18102/health`
- 配置信息：`http://localhost:18102/config`

## 配置说明

### 本地配置文件

Fetcher 服务使用 `config/config.yaml` 作为本地配置文件，包含以下主要配置项：

```yaml
# 代理配置
proxy:
  enabled: true
  url: "http://127.0.0.1:1080"

# Celery配置
celery:
  broker_url: "amqp://guest:guest@localhost:5672//"
  result_backend: "rpc://"
  timezone: "UTC"
  enable_utc: true

# Twitter API配置
twitter:
  api_key: ""
  api_secret: ""
  access_token: ""
  access_secret: ""
  endpoints:
    similar_users: "https://x.com/i/api/graphql/WIeRrT1lB03IHxrLKXcY3g/ConnectTabTimeline"

# FastAPI 配置
fastapi:
  title: Fetcher Service
  description: Service for fetching data from various sources
  version: 0.1.0
  docs_url: /docs
  redoc_url: /redoc
  openapi_url: /openapi.json
  
# Nacos 配置
nacos:
  enabled: true
  config_file: config/nacos_config.yaml
```

### Nacos 配置

Nacos 配置文件位于 `config/nacos_config.yaml`，包含以下配置项：

```yaml
nacos:
  server_addr: ${NACOS_SERVER_ADDR}
  namespace: ${NACOS_NAMESPACE}
  username: ${NACOS_USERNAME}
  password: ${NACOS_PASSWORD}
  data_id: fetcher-service
  group: DEFAULT_GROUP
  timeout: 5
  
service:
  name: fetcher-service
  ip: ${HOST_IP}
  port: 8000
  weight: 1
  cluster_name: DEFAULT
  group_name: DEFAULT_GROUP
  ephemeral: true
```

## API 接口

Fetcher 服务提供以下主要 API 接口：

- `GET /`: 欢迎页面
- `GET /health`: 健康检查
- `GET /task/{task_id}`: 获取任务状态和结果
- `POST /fetch`: 提交抓取任务

## 服务发现与注册

Fetcher 服务在启动时会自动向 Nacos 注册，并在关闭时注销。可以在 Nacos 控制台的服务列表中查看注册状态。

## 生产环境部署建议

1. 使用 Gunicorn 或 Uvicorn 作为 WSGI/ASGI 服务器
2. 配置适当的工作进程数和线程数
3. 设置合理的超时时间和重试策略
4. 使用 Nginx 或其他反向代理服务器
5. 实现健康检查和自动恢复机制
6. 配置日志收集和监控系统

## 贡献与支持

如有问题或建议，请提交 Issue 或 Pull Request。