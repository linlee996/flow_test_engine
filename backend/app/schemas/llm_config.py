"""LLM 厂商配置 Schema"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ===== 厂商配置 =====

class ProviderConfigBase(BaseModel):
    """厂商配置基础"""
    base_url: str
    api_key: str


class ProviderConfigUpdate(ProviderConfigBase):
    """更新厂商配置"""
    pass


class ProviderModelResponse(BaseModel):
    """模型信息响应"""
    id: int
    model_name: str
    is_custom: bool
    
    class Config:
        from_attributes = True


class ProviderConfigResponse(BaseModel):
    """厂商配置响应"""
    id: int
    provider: str
    base_url: str
    is_available: bool
    models: list[ProviderModelResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProviderListItem(BaseModel):
    """厂商列表项（左侧列表用）"""
    provider: str
    name: str  # 显示名称
    is_configured: bool  # 是否已配置
    is_available: bool  # 连接是否可用
    model_count: int  # 模型数量


class TestConnectionRequest(BaseModel):
    """测试连接请求"""
    base_url: str
    api_key: str


class TestConnectionResponse(BaseModel):
    """测试连接响应"""
    success: bool
    message: str


class FetchModelsRequest(BaseModel):
    """获取模型请求"""
    base_url: str
    api_key: str


class FetchModelsResponse(BaseModel):
    """获取模型响应"""
    success: bool
    models: list[str]
    message: Optional[str] = None


class AddModelRequest(BaseModel):
    """手动添加模型请求"""
    model_name: str


# ===== 用于 Task 创建时的模型选择 =====

class ModelOption(BaseModel):
    """模型选项"""
    model_name: str
    provider: str


class ProviderModelGroup(BaseModel):
    """厂商模型分组（用于下拉选择）"""
    provider: str
    name: str  # 厂商显示名称
    models: list[str]



