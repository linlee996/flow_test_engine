"""Embedding 服务 - 复用已配置的 LLM 厂商 API 创建 Embedding 实例"""
from langchain_openai import OpenAIEmbeddings
from langchain_core.embeddings import Embeddings


# 各厂商的默认 Embedding 模型和支持状态
EMBEDDING_PROVIDER_DEFAULTS = {
    "openai": {
        "name": "OpenAI",
        "default_model": "text-embedding-3-small",
        "supported": True,
    },
    "gemini": {
        "name": "Gemini",
        "default_model": "text-embedding-004",
        "supported": True,
    },
    "openrouter": {
        "name": "OpenRouter",
        "default_model": "openai/text-embedding-3-small",
        "supported": True,
    },
    "deepseek": {
        "name": "DeepSeek",
        "default_model": "",
        "supported": False,
    },
    "kimi": {
        "name": "Kimi",
        "default_model": "",
        "supported": False,
    },
    "anthropic": {
        "name": "Anthropic",
        "default_model": "",
        "supported": False,
    },
}


def create_embeddings(provider: str, api_key: str, base_url: str, model: str) -> Embeddings:
    """
    根据厂商创建 LangChain Embeddings 实例
    复用已配置的 LLM 厂商 API key 和 base_url
    """
    provider = provider.lower() if provider else "openai"

    # Gemini 单独处理
    if provider == "gemini":
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            return GoogleGenerativeAIEmbeddings(
                model=model,
                google_api_key=api_key,
            )
        except ImportError:
            # 回退到 OpenAI 兼容模式
            return OpenAIEmbeddings(
                model=model,
                api_key=api_key,
                base_url=f"{base_url.rstrip('/')}/v1beta/openai",
            )

    # OpenAI / OpenRouter / 其他兼容 OpenAI 格式的厂商
    kwargs = {
        "model": model,
        "api_key": api_key,
    }
    if base_url:
        kwargs["base_url"] = f"{base_url.rstrip('/')}/v1"

    return OpenAIEmbeddings(**kwargs)


def is_embedding_supported(provider: str) -> bool:
    """检查厂商是否支持 Embedding API"""
    info = EMBEDDING_PROVIDER_DEFAULTS.get(provider.lower(), {})
    return info.get("supported", False)


def get_default_embedding_model(provider: str) -> str:
    """获取厂商默认的 Embedding 模型名"""
    info = EMBEDDING_PROVIDER_DEFAULTS.get(provider.lower(), {})
    return info.get("default_model", "")
