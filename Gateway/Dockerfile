FROM golang:1.20-alpine AS builder

WORKDIR /app

# 复制go mod文件
COPY go.mod ./
# 下载依赖并生成 go.sum
RUN go mod download && go mod tidy

# 复制源代码
COPY . .

# Add build arguments for proxy
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

# Set proxy environment variables for the build
ENV HTTP_PROXY=$HTTP_PROXY
ENV HTTPS_PROXY=$HTTPS_PROXY
ENV NO_PROXY=$NO_PROXY

# 编译
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o gateway ./cmd/main.go

# 运行阶段
FROM alpine:latest

# 更新包索引并安装证书
RUN apk update && \
    apk add --no-cache ca-certificates && \
    update-ca-certificates

WORKDIR /root/

# 从构建阶段复制可执行文件
COPY --from=builder /app/gateway .

# 暴露端口
EXPOSE 8080

# 启动命令
CMD ["./gateway"] 