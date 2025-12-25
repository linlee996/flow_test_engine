"""模板相关 Schema"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class TemplateField(BaseModel):
    name: str
    description: str


class TemplateCreate(BaseModel):
    name: str
    fields: list[TemplateField]
    is_default: bool = False


class TemplateUpdate(BaseModel):
    id: int
    name: str
    fields: list[TemplateField]
    is_default: bool = False


class TemplateResponse(BaseModel):
    id: int
    name: str
    fields: list[dict]
    is_default: bool
    is_system: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
