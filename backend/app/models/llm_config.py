"""LLM 厂商配置模型"""
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class LLMProvider:
    """支持的 LLM 厂商"""
    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    KIMI = "kimi"  # Moonshot
    OPENROUTER = "openrouter"  # 聚合多厂商的API网关


# 厂商默认配置
# 用户只需输入 base_url（host），接口路径由代码自动补全
PROVIDER_DEFAULTS = {
    LLMProvider.OPENAI: {
        "name": "OpenAI",
        "base_url": "https://api.openai.com",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    },
    LLMProvider.GEMINI: {
        "name": "Gemini",
        "base_url": "https://generativelanguage.googleapis.com",
        "models": ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"],
    },
    LLMProvider.ANTHROPIC: {
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com",
        "models": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
    },
    LLMProvider.DEEPSEEK: {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "models": ["deepseek-chat", "deepseek-coder"],
    },
    LLMProvider.KIMI: {
        "name": "Kimi",
        "base_url": "https://api.moonshot.cn",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
    },
    LLMProvider.OPENROUTER: {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api",
        "models": ["openai/gpt-4o", "anthropic/claude-3.5-sonnet", "google/gemini-2.0-flash-exp"],
    },
}

# 厂商排序优先级
PROVIDER_ORDER = [
    LLMProvider.OPENAI,
    LLMProvider.GEMINI,
    LLMProvider.ANTHROPIC,
    LLMProvider.DEEPSEEK,
    LLMProvider.KIMI,
    LLMProvider.OPENROUTER,
]


class ProviderConfig(Base):
    """厂商配置 - 每个用户每个厂商一条记录"""
    __tablename__ = "provider_config"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, comment="厂商标识")
    base_url: Mapped[str] = mapped_column(String(500), nullable=False, comment="API Host（不含路径）")
    api_key: Mapped[str] = mapped_column(Text, nullable=False, comment="API Key")
    is_available: Mapped[bool] = mapped_column(Boolean, default=False, comment="连接是否可用")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联模型列表
    models: Mapped[list["ProviderModel"]] = relationship(
        "ProviderModel", back_populates="provider_config", cascade="all, delete-orphan"
    )

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )


class ProviderModel(Base):
    """厂商模型 - 每个厂商配置关联多个模型"""
    __tablename__ = "provider_model"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    provider_config_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("provider_config.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="模型名称")
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否用户自定义添加")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关联厂商配置
    provider_config: Mapped["ProviderConfig"] = relationship("ProviderConfig", back_populates="models")



