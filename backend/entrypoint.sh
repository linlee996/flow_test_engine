#!/bin/bash
set -e

# 确保必要的目录存在
mkdir -p /app/backend/data
mkdir -p /app/backend/uploads
mkdir -p /app/backend/outputs
mkdir -p /app/backend/logs

# 启动应用
exec /app/backend/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
