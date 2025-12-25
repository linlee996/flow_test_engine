"""配置管理"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

# 获取项目根目录（backend 目录）
_BACKEND_DIR = Path(__file__).parent.parent.parent.resolve()


class Settings(BaseSettings):
    # 基础配置
    app_name: str = "Flow Test Engine"
    debug: bool = False

    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8080

    # JWT配置
    jwt_secret: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # 数据库配置 - 默认使用相对路径，docker 环境可通过环境变量覆盖
    database_url: str = f"sqlite+aiosqlite:///{_BACKEND_DIR / 'data' / 'flow_test.db'}"

    # 文件配置 - 默认使用相对路径
    upload_dir: str = str(_BACKEND_DIR / "uploads")
    output_dir: str = str(_BACKEND_DIR / "outputs")
    max_file_size: int = 52428800  # 50MB

    # 内置管理员账号
    admin_username: str = "admin"
    admin_password: str = "admin"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
