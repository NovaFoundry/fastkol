# 启动指南

## 快速启动

### 1. 启动 Docker 环境

```bash
# 进入 Docker 环境目录
cd docker/environments/dev
docker compose up -d
```

### 2. Consul 及 Token 配置

1. **启动 Consul**：确保 Consul 服务已启动（见上方 Docker 启动步骤，或单独启动 Consul 容器）。
2. **创建 Token**：在 Consul 中执行脚本：

   ```bash
   CONSUL_HTTP_TOKEN=your-master-token /consul/create-consul-tokens.sh
   ```
3. **配置 Token**：将生成的 Token 写入各服务的配置文件或环境变量中，供服务注册、发现等功能使用。

### 3. 启动Fetcher
请参考 [Fetcher 服务启动指南](Fetcher/README.md) 获取完整的启动说明，包括：

- 环境要求
- 依赖安装
- API 服务启动
- 配置说明
- API 接口文档
- 服务发现与注册
- 生产环境部署建议
