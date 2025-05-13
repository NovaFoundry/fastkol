# 第一阶段：构建 Go 二进制
FROM golang:1.24 AS builder

WORKDIR /app

# 安装 git 以支持 go mod 下载私有依赖（如有需要）
RUN apk add --no-cache git

# 拷贝 go.mod 和 go.sum 并下载依赖
COPY go.mod go.sum ./
RUN go mod download

# 拷贝项目源码
COPY . .

# 初始化项目
RUN make all
# 构建二进制文件
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o admin ./cmd/Admin

# 第二阶段：极简运行环境
FROM alpine:3.21

WORKDIR /app

# 拷贝配置文件（如有需要可调整路径）
COPY --from=builder /app/admin ./

# 设置时区（可选）
# RUN apk add --no-cache tzdata

# 暴露服务端口（根据你的服务端口调整）
EXPOSE 8000 9000

# 启动命令
CMD ["./admin", "-conf", "./configs/config.yaml"]
