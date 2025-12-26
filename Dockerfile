# 阶段1: 构建前端
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --production=false

COPY frontend/ ./
RUN npm run build

# 阶段2: 构建 Python 环境
FROM python:3.13-slim AS backend-builder

# 安装系统依赖 - OpenCV 和 OCR 需要的库 + 构建工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app/backend

# 复制依赖文件
COPY backend/pyproject.toml backend/uv.lock* backend/README.md ./

# 安装依赖到 .venv
RUN uv sync --no-dev

# 清理 uv 缓存和不必要的文件，减小镜像体积
RUN uv cache clean && \
    find .venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find .venv -type f -name "*.pyc" -delete && \
    find .venv -type f -name "*.pyo" -delete

# 复制应用代码
COPY backend/ ./

# 阶段3: 最终运行镜像
FROM python:3.13-slim

# 安装运行时系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 从前端构建阶段复制静态文件
COPY --from=frontend-builder /app/frontend/dist /app/static

# 从后端构建阶段复制 Python 环境和代码
COPY --from=backend-builder /app/backend /app/backend

# 删除backend目录下可能存在的data、uploads、outputs目录
RUN rm -rf /app/backend/data /app/backend/uploads /app/backend/outputs /app/backend/logs

# 复制启动脚本并设置执行权限
COPY backend/entrypoint.sh /app/backend/entrypoint.sh
RUN chmod +x /app/backend/entrypoint.sh

# 设置环境变量
ENV PATH="/app/backend/.venv/bin:$PATH" \
    PYTHONPATH=/app/backend \
    PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 8080

# 工作目录切换到 backend
WORKDIR /app/backend

# 使用启动脚本
CMD ["/app/backend/entrypoint.sh"]
