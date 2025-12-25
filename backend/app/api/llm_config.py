"""LLM 厂商配置 API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core import get_db
from app.models import (
    PROVIDER_DEFAULTS, PROVIDER_ORDER,
    ProviderConfig, ProviderModel
)
from app.schemas.llm_config import (
    ProviderConfigUpdate, ProviderConfigResponse, ProviderListItem,
    TestConnectionRequest, TestConnectionResponse,
    FetchModelsRequest, FetchModelsResponse,
    AddModelRequest, ProviderModelGroup
)
from app.services import llm_service

router = APIRouter()


# ===== 厂商配置 API =====

@router.get("/provider-list", response_model=list[ProviderListItem])
async def get_provider_list(db: AsyncSession = Depends(get_db)):
    """获取厂商列表（左侧导航用）"""
    # 获取已配置的厂商，使用 selectinload 避免 lazy loading 问题
    result = await db.execute(
        select(ProviderConfig).options(selectinload(ProviderConfig.models))
    )
    user_configs = {c.provider: c for c in result.scalars().all()}
    
    items = []
    for provider in PROVIDER_ORDER:
        defaults = PROVIDER_DEFAULTS.get(provider, {})
        config = user_configs.get(provider)
        
        items.append(ProviderListItem(
            provider=provider,
            name=defaults.get("name", provider),
            is_configured=config is not None,
            is_available=config.is_available if config else False,
            model_count=len(config.models) if config else len(defaults.get("models", [])),
        ))
    
    return items


@router.get("/provider-configs/{provider}", response_model=ProviderConfigResponse | None)
async def get_provider_config(
    provider: str,
    db: AsyncSession = Depends(get_db),
):
    """获取指定厂商配置"""
    result = await db.execute(
        select(ProviderConfig)
        .where(ProviderConfig.provider == provider)
        .options(selectinload(ProviderConfig.models))
    )
    config = result.scalar_one_or_none()
    return config


@router.put("/provider-configs/{provider}", response_model=ProviderConfigResponse)
async def upsert_provider_config(
    provider: str,
    data: ProviderConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    """创建或更新厂商配置"""
    # 检查厂商是否有效
    if provider not in PROVIDER_DEFAULTS:
        raise HTTPException(status_code=400, detail="不支持的厂商")
    
    # 查找现有配置
    result = await db.execute(
        select(ProviderConfig)
        .where(ProviderConfig.provider == provider)
        .options(selectinload(ProviderConfig.models))
    )
    config = result.scalar_one_or_none()
    
    if config:
        # 更新现有配置
        # 非 openai 厂商使用默认 base_url
        if provider == "openai":
            config.base_url = data.base_url
        else:
            config.base_url = PROVIDER_DEFAULTS.get(provider, {}).get("base_url", data.base_url)
        if data.api_key:
            config.api_key = data.api_key
        config.is_available = False  # 重置，需要重新测试
    else:
        # 创建新配置
        # 非 openai 厂商使用默认 base_url
        if provider == "openai":
            base_url = data.base_url
        else:
            base_url = PROVIDER_DEFAULTS.get(provider, {}).get("base_url", data.base_url)
        config = ProviderConfig(
            provider=provider,
            base_url=base_url,
            api_key=data.api_key,
            is_available=False,
        )
        db.add(config)
        await db.flush()  # 获取 ID
        
        # 添加默认模型
        default_models = PROVIDER_DEFAULTS.get(provider, {}).get("models", [])
        for model_name in default_models:
            model = ProviderModel(
                provider_config_id=config.id,
                model_name=model_name,
                is_custom=False,
            )
            db.add(model)
    
    await db.commit()
    
    # 重新查询以获取包含 models 的完整对象
    result = await db.execute(
        select(ProviderConfig)
        .where(ProviderConfig.id == config.id)
        .options(selectinload(ProviderConfig.models))
    )
    config = result.scalar_one()
    return config


@router.post("/provider-configs/{provider}/models/{model_name:path}/test", response_model=TestConnectionResponse)
async def test_model_connection(
    provider: str,
    model_name: str,
    data: TestConnectionRequest,
    db: AsyncSession = Depends(get_db),
):
    """测试特定模型连接"""
    # 如果请求中没有 API Key，从数据库获取已保存的
    api_key = data.api_key
    base_url = data.base_url
    
    # 查找配置（始终需要，因为可能需要回退 API Key 或 Base URL）
    result = await db.execute(
        select(ProviderConfig).where(ProviderConfig.provider == provider)
    )
    saved_config = result.scalar_one_or_none()
    
    if not api_key:
        if saved_config:
            api_key = saved_config.api_key
        else:
            return TestConnectionResponse(success=False, message="请先保存配置")
            
    # 如果请求中没有 Base URL，也可以使用保存的
    if not base_url and saved_config:
        base_url = saved_config.base_url

    success, message = await llm_service.test_connection(
        provider=provider,
        base_url=base_url,
        api_key=api_key,
        model=model_name,
    )
    
    # 如果测试成功，更新配置状态
    if success and saved_config:
        saved_config.is_available = True
        await db.commit()
    
    return TestConnectionResponse(success=success, message=message)


@router.post("/provider-configs/{provider}/fetch-models", response_model=FetchModelsResponse)
async def fetch_provider_models(
    provider: str,
    data: FetchModelsRequest,
    db: AsyncSession = Depends(get_db),
):
    """获取厂商可用模型"""
    api_key = data.api_key
    base_url = data.base_url
    
    saved_config = None
    if not api_key or not base_url:
        result = await db.execute(
            select(ProviderConfig).where(ProviderConfig.provider == provider)
        )
        saved_config = result.scalar_one_or_none()
    
    if not api_key:
        if saved_config:
            api_key = saved_config.api_key
        else:
            return FetchModelsResponse(success=False, models=[], message="请先保存配置")
            
    if not base_url and saved_config:
        base_url = saved_config.base_url
    
    models, error = await llm_service.fetch_models(
        provider=provider,
        base_url=base_url,
        api_key=api_key,
    )
    
    if error:
        return FetchModelsResponse(success=False, models=[], message=error)
    
    result = await db.execute(
        select(ProviderConfig)
        .where(ProviderConfig.provider == provider)
        .options(selectinload(ProviderConfig.models))
    )
    config = result.scalar_one_or_none()
    
    if config:
        # 删除非自定义模型
        for m in list(config.models):
            if not m.is_custom:
                await db.delete(m)
        
        # 添加新获取的模型
        for model_name in models:
            model = ProviderModel(
                provider_config_id=config.id,
                model_name=model_name,
                is_custom=False,
            )
            db.add(model)
        
        config.is_available = True
        await db.commit()
    
    return FetchModelsResponse(success=True, models=models, message=None)


@router.post("/provider-configs/{provider}/models")
async def add_provider_model(
    provider: str,
    data: AddModelRequest,
    db: AsyncSession = Depends(get_db),
):
    """手动添加模型"""
    result = await db.execute(
        select(ProviderConfig)
        .where(ProviderConfig.provider == provider)
        .options(selectinload(ProviderConfig.models))
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="请先配置厂商")
    
    existing = [m.model_name for m in config.models]
    if data.model_name in existing:
        raise HTTPException(status_code=400, detail="模型已存在")
    
    model = ProviderModel(
        provider_config_id=config.id,
        model_name=data.model_name,
        is_custom=True,
    )
    db.add(model)
    await db.commit()
    
    return {"message": "添加成功"}


@router.delete("/provider-configs/{provider}/models/{model_name:path}")
async def delete_provider_model(
    provider: str,
    model_name: str,
    db: AsyncSession = Depends(get_db),
):
    """删除模型"""
    result = await db.execute(
        select(ProviderConfig)
        .where(ProviderConfig.provider == provider)
        .options(selectinload(ProviderConfig.models))
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="厂商配置不存在")
    
    target_model = None
    for m in config.models:
        if m.model_name == model_name:
            target_model = m
            break
    
    if not target_model:
        raise HTTPException(status_code=404, detail="模型不存在")
    
    await db.delete(target_model)
    await db.commit()
    
    return {"message": "删除成功"}


@router.get("/model-groups", response_model=list[ProviderModelGroup])
async def get_model_groups(db: AsyncSession = Depends(get_db)):
    """获取所有已配置厂商的模型分组（用于 Task 创建时的下拉选择）"""
    result = await db.execute(
        select(ProviderConfig).options(selectinload(ProviderConfig.models))
    )
    configs = result.scalars().all()
    
    config_map = {c.provider: c for c in configs}
    
    groups = []
    for provider in PROVIDER_ORDER:
        config = config_map.get(provider)
        if config and config.models:
            defaults = PROVIDER_DEFAULTS.get(provider, {})
            groups.append(ProviderModelGroup(
                provider=provider,
                name=defaults.get("name", provider),
                models=[m.model_name for m in config.models],
            ))
    
    return groups
