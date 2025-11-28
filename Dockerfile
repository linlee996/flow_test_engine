# 阶段1: 构建前端
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --production=false

COPY frontend/ ./
RUN npm run build

# 阶段2: 构建 Go 后端
FROM golang:1.24-bookworm AS backend-builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y \
    gcc \
    libc-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY go.mod go.sum ./
RUN go mod download

# 复制源码
COPY . .

# 构建后端（启用 CGO 支持 SQLite）
# 移除 GOARCH 参数，让 Go 自动检测当前架构（ARM64 或 AMD64）
RUN CGO_ENABLED=1 GOOS=linux go build -o flow_test_engine ./cmd/api

# 最终阶段：运行环境
FROM debian:bookworm-slim

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /app/data /app/uploads /app/outputs /app/logs /app/config

WORKDIR /app

# 从后端构建阶段复制二进制文件
COPY --from=backend-builder /app/flow_test_engine /app/

# 从前端构建阶段复制静态文件到 static 目录
COPY --from=frontend-builder /app/frontend/dist /app/static

# 复制配置文件
COPY config /app/config

# 设置权限
RUN chmod +x /app/flow_test_engine

# 暴露端口
EXPOSE 8080

# 设置数据卷
VOLUME ["/app/data", "/app/uploads", "/app/outputs", "/app/logs", "/app/config"]

# 启动命令
CMD ["/app/flow_test_engine"]
