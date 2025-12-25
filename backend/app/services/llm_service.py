"""LLM 服务层 - 处理与 LLM API 的交互

各厂商 API 端点配置：
- OpenAI:    /v1/models (GET, Bearer Token)
- Gemini:    /v1beta/openai/models (GET, x-goog-api-key)
- Anthropic: /v1/models (GET, x-api-key)
- DeepSeek:  /v1/models (GET, Bearer Token)
- Kimi:      /v1/models (GET, Bearer Token)
"""
import httpx
from typing import Optional


# 各厂商的 API 路径和认证方式配置
PROVIDER_API_CONFIG = {
    "openai": {
        "models_path": "/v1/models",
        "chat_path": "/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
    },
    "gemini": {
        "models_path": "/v1beta/openai/models",
        "chat_path": "/v1beta/models/{model}:generateContent",
        "auth_header": "x-goog-api-key",
        "auth_prefix": "",  # Gemini 直接使用 API Key
    },
    "anthropic": {
        "models_path": "/v1/models",
        "chat_path": "/v1/messages",
        "auth_header": "x-api-key",
        "auth_prefix": "",  # Anthropic 直接使用 API Key
    },
    "deepseek": {
        "models_path": "/v1/models",
        "chat_path": "/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
    },
    "kimi": {
        "models_path": "/v1/models",
        "chat_path": "/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
    },
    "openrouter": {
        "models_path": "/v1/models",
        "chat_path": "/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
    },
}


def _get_headers(provider: str, api_key: str) -> dict:
    """根据厂商获取正确的认证头"""
    config = PROVIDER_API_CONFIG.get(provider, PROVIDER_API_CONFIG["openai"])
    auth_header = config["auth_header"]
    auth_prefix = config["auth_prefix"]
    
    headers = {
        "Content-Type": "application/json",
        auth_header: f"{auth_prefix}{api_key}",
    }
    
    # Anthropic 需要额外的版本头
    if provider == "anthropic":
        headers["anthropic-version"] = "2023-06-01"
    
    return headers


def _get_models_url(provider: str, base_url: str) -> str:
    """获取模型列表 API URL"""
    config = PROVIDER_API_CONFIG.get(provider, PROVIDER_API_CONFIG["openai"])
    return f"{base_url.rstrip('/')}{config['models_path']}"


def _get_chat_url(provider: str, base_url: str, model: str = "") -> str:
    """获取聊天 API URL"""
    config = PROVIDER_API_CONFIG.get(provider, PROVIDER_API_CONFIG["openai"])
    chat_path = config["chat_path"]
    if "{model}" in chat_path:
        chat_path = chat_path.replace("{model}", model)
    return f"{base_url.rstrip('/')}{chat_path}"


def _build_chat_payload(provider: str, model: str) -> dict:
    """构建不同厂商的 Chat API 请求体"""
    if provider == "gemini":
        return {
            "contents": [{"parts": [{"text": "hi"}]}],
            "generationConfig": {"maxOutputTokens": 10}
        }
    elif provider == "anthropic":
        return {
            "model": model,
            "max_tokens": 10,
            "messages": [{"role": "user", "content": "hi"}],
            "anthropic_version": "2023-06-01"
        }
    else:
        # OpenAI, DeepSeek, Kimi
        return {
            "model": model,
            "stream": False,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 10
        }


async def test_connection(
    provider: str,
    base_url: str,
    api_key: str,
    model: str,
    timeout: float = 10.0
) -> tuple[bool, str]:
    """
    测试模型连接是否可用
    通过调用 Chat API 来测试
    
    Returns:
        (success, message)
    """
    try:
        url = _get_chat_url(provider, base_url, model)
        headers = _get_headers(provider, api_key)
        payload = _build_chat_payload(provider, model)
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                return True, "连接成功"
            elif response.status_code == 401:
                return False, "API Key 无效"
            elif response.status_code == 403:
                return False, "API Key 权限不足"
            elif response.status_code == 404:
                return False, f"API 端点不存在: {url}"
            else:
                # 尝试解析错误信息
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "") or str(error_data)
                    return False, f"连接失败: {error_msg[:100]}"
                except Exception:
                    return False, f"连接失败: HTTP {response.status_code}"
                
    except httpx.TimeoutException:
        return False, "连接超时"
    except httpx.ConnectError:
        return False, "无法连接到服务器"
    except Exception as e:
        return False, f"连接错误: {str(e)}"


async def fetch_models(
    provider: str,
    base_url: str,
    api_key: str,
    timeout: float = 15.0
) -> tuple[list[str], Optional[str]]:
    """
    从 API 获取可用模型列表

    Returns:
        (models, error_message)
    """
    try:
        url = _get_models_url(provider, base_url)
        headers = _get_headers(provider, api_key)

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, headers=headers)

            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "") or str(error_data)
                    return [], f"获取失败: {error_msg[:100]}"
                except Exception:
                    # 尝试获取响应文本
                    text = response.text[:200] if response.text else "无响应内容"
                    return [], f"HTTP {response.status_code}: {text}"

            # 尝试解析 JSON
            try:
                data = response.json()
            except Exception as e:
                text = response.text[:200] if response.text else "空响应"
                return [], f"JSON解析失败: {text}"
            
            # OpenAI 格式: {"data": [{"id": "model-name", ...}, ...]}
            if "data" in data and isinstance(data["data"], list):
                models = []
                for item in data["data"]:
                    if isinstance(item, dict) and "id" in item:
                        models.append(item["id"])
                    elif isinstance(item, str):
                        models.append(item)
                
                # 按字母顺序排序
                models.sort()
                return models, None
            
            # 其他格式尝试
            if "models" in data and isinstance(data["models"], list):
                models = []
                for item in data["models"]:
                    if isinstance(item, dict):
                        name = item.get("name") or item.get("model") or item.get("id")
                        if name:
                            models.append(name)
                    elif isinstance(item, str):
                        models.append(item)
                models.sort()
                return models, None
            
            return [], "无法解析模型列表格式"
            
    except httpx.TimeoutException:
        return [], "请求超时"
    except httpx.ConnectError:
        return [], "无法连接到服务器"
    except Exception as e:
        return [], f"获取错误: {str(e)}"


def get_chat_url(provider: str, base_url: str, model: str = "") -> str:
    """获取聊天 API URL（供外部调用）"""
    return _get_chat_url(provider, base_url, model)


def get_chat_headers(provider: str, api_key: str) -> dict:
    """获取聊天 API 请求头（供外部调用）"""
    return _get_headers(provider, api_key)
