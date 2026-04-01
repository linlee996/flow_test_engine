"""知识库相关 Schema"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ========== 项目 ==========

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    embedding_provider: str
    embedding_model: str


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    embedding_provider: Optional[str] = None
    embedding_model: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    embedding_provider: str
    embedding_model: str
    doc_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    total: int
    projects: list[ProjectResponse]


# ========== 知识库文档 ==========

class KnowledgeDocumentResponse(BaseModel):
    id: int
    project_id: int
    original_filename: str
    file_size: int
    chunk_count: int
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ========== 检索 ==========

class KnowledgeSearchRequest(BaseModel):
    query: str
    top_k: int = 5


class KnowledgeSearchResult(BaseModel):
    content: str
    metadata: dict
    distance: float


class KnowledgeSearchResponse(BaseModel):
    results: list[KnowledgeSearchResult]


# ========== Embedding 厂商 ==========

class EmbeddingProviderInfo(BaseModel):
    provider: str
    name: str
    default_model: str
    is_configured: bool
