# 选择官方 Node.js Alpine 镜像作为构建阶段
FROM node:22.15.0-alpine3.21 AS builder

WORKDIR /app

COPY package.json package-lock.json ./
# 安装构建原生依赖所需工具
RUN apk add --no-cache python3 make g++
RUN npm ci

COPY . .
RUN mkdir -p public
RUN npm run build

# 生产环境镜像
FROM node:22.15.0-alpine3.21 AS runner
WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /app/package.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["npm", "run", "start"]