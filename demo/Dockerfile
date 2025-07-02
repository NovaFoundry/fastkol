# 选择官方 Node.js Alpine 镜像作为构建阶段
FROM node:22.15.0-alpine3.21 AS builder

WORKDIR /app

# 安装pnpm
RUN npm install -g pnpm

# 复制package.json和pnpm-lock.yaml（如果有）
COPY package.json ./
COPY pnpm-lock.yaml ./

# 安装构建原生依赖所需工具
RUN apk add --no-cache python3 make g++

# 使用pnpm的高效依赖安装
RUN pnpm install --frozen-lockfile --prod=false

# 复制源代码
COPY . .
COPY .env* ./
RUN mkdir -p public

# 构建应用
RUN pnpm build

# 生产环境镜像 - 使用更小的基础镜像
FROM node:22.15.0-alpine3.21 AS runner
WORKDIR /app

ENV NODE_ENV=production

# 安装pnpm - 仅安装不需要额外依赖
RUN npm install -g pnpm --no-fund --no-audit

# 只复制生产所需文件
COPY --from=builder /app/package.json ./
COPY --from=builder /app/pnpm-lock.yaml ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/.env* ./

# 只安装生产依赖
RUN pnpm install --prod --frozen-lockfile

EXPOSE 3000

CMD ["pnpm", "start"]