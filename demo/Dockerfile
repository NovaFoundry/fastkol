# 选择官方 Node.js 镜像，建议和 package.json 里的 node 版本一致
FROM node:22.15.0-slim

# 设置工作目录
WORKDIR /app

# 复制 package.json 和 package-lock.json
COPY package.json package-lock.json ./

# 安装依赖
RUN npm ci

# 复制所有源代码
COPY . .

# 暴露 Next.js 默认端口
EXPOSE 3000

# 启动开发服务器，支持热更新
CMD ["npm", "run", "dev", "--", "-H", "0.0.0.0"]