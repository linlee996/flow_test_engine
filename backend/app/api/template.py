"""模板管理 API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core import get_db
from app.models import CaseTemplate
from app.schemas import TemplateCreate, TemplateUpdate, TemplateResponse

router = APIRouter()


@router.get("", response_model=list[TemplateResponse])
async def get_templates(db: AsyncSession = Depends(get_db)):
    """获取模板列表"""
    result = await db.execute(
        select(CaseTemplate).order_by(CaseTemplate.is_default.desc(), CaseTemplate.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=TemplateResponse)
async def create_template(
    data: TemplateCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建模板"""
    # 如果设为默认，先取消其他默认
    if data.is_default:
        await _clear_default_templates(db)

    template = CaseTemplate(
        name=data.name,
        fields=[field.model_dump() for field in data.fields],
        is_default=data.is_default,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.put("", response_model=TemplateResponse)
async def update_template(
    data: TemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新模板"""
    result = await db.execute(
        select(CaseTemplate).where(CaseTemplate.id == data.id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    if template.is_system:
        raise HTTPException(status_code=400, detail="系统模板不可修改")

    if data.is_default:
        await _clear_default_templates(db)

    template.name = data.name
    template.fields = [field.model_dump() for field in data.fields]
    template.is_default = data.is_default
    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除模板"""
    result = await db.execute(
        select(CaseTemplate).where(CaseTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    if template.is_system:
        raise HTTPException(status_code=400, detail="系统模板不可删除")

    await db.delete(template)
    await db.commit()
    return {"message": "删除成功"}


async def _clear_default_templates(db: AsyncSession):
    """清除默认模板标记"""
    result = await db.execute(
        select(CaseTemplate).where(CaseTemplate.is_default == True)
    )
    for t in result.scalars():
        t.is_default = False
