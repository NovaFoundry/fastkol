# 使用更新的 golang 基础镜像
FROM golang:1.24-alpine3.21 AS builder

WORKDIR /app

# 设置 Go 环境变量
ENV GO111MODULE=on \
    CGO_ENABLED=0 \
    GOOS=linux \
    GOARCH=amd64

# 添加构建代理参数
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

# 设置构建代理环境变量
ENV HTTP_PROXY=$HTTP_PROXY \
    HTTPS_PROXY=$HTTPS_PROXY \
    NO_PROXY=$NO_PROXY

# 首先只复制go.mod文件
COPY go.mod ./

# 初始化go.mod并下载依赖
RUN go mod tidy

# 复制源代码
COPY . .

# 编译
RUN go build -o gateway ./cmd/main.go

# 使用最新的 alpine 作为运行基础镜像
FROM alpine:3.21

# 添加运行时依赖
RUN apk update && \
    apk add --no-cache ca-certificates tzdata && \
    update-ca-certificates && \
    # 清理缓存
    rm -rf /var/cache/apk/*

WORKDIR /app

# 从构建阶段复制可执行文件
COPY --from=builder /app/gateway .

# 暴露端口
EXPOSE 8080

# 使用非 root 用户运行
RUN adduser -D -g '' appuser
USER appuser

# 启动命令
ENTRYPOINT ["./gateway"] 