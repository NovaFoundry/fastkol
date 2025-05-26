# 构建阶段
FROM node:22.15.0-alpine3.21 AS builder

WORKDIR /app

COPY package.json package-lock.json ./
# 安装构建原生依赖所需工具
RUN apk add --no-cache python3 make g++
RUN npm ci

COPY . .
COPY .env* ./

# 新增：声明构建参数
ARG API_BASE_URL
ARG API_GATEWAY_URL

# 新增：将构建参数转为环境变量
ENV API_BASE_URL=${API_BASE_URL}
ENV API_GATEWAY_URL=${API_GATEWAY_URL}

RUN mkdir -p public
RUN npm run build

# 生产环境阶段
FROM node:22.15.0-alpine3.21 AS runner
WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /app/package.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/.env* ./

EXPOSE 3000

CMD ["npm", "run", "start"] 