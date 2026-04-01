"""知识库管理 API - 项目 CRUD、文档上传/删除、检索"""
import uuid
import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core import get_db, get_settings
from app.models import Project, KnowledgeDocument, ProviderConfig
from app.schemas.knowledge import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse,
    KnowledgeDocumentResponse, KnowledgeSearchRequest, KnowledgeSearchResponse,
    KnowledgeSearchResult, EmbeddingProviderInfo,
)
from app.services.knowledge_service import KnowledgeBaseService
from app.services.embedding_service import (
    create_embeddings, is_embedding_supported,
    EMBEDDING_PROVIDER_DEFAULTS,
)

router = APIRouter()
settings = get_settings()
_kb_service = KnowledgeBaseService()


# ========== Embedding 厂商信息 ==========

@router.get("/embedding-providers", response_model=list[EmbeddingProviderInfo])
async def get_embedding_providers(db: AsyncSession = Depends(get_db)):
    """获取支持 Embedding 的厂商列表（只返回已配置且支持 Embedding 的厂商）"""
    # 查询所有已配置的厂商
    result = await db.execute(select(ProviderConfig))
    configs = result.scalars().all()
    configured_providers = {c.provider for c in configs}

    providers = []
    for provider, info in EMBEDDING_PROVIDER_DEFAULTS.items():
        if info["supported"]:
            providers.append(EmbeddingProviderInfo(
                provider=provider,
                name=info["name"],
                default_model=info["default_model"],
                is_configured=provider in configured_providers,
            ))

    return providers


# ========== 项目管理 ==========

@router.post("/projects", response_model=ProjectResponse)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    """创建项目"""
    # 检查名称是否重复
    result = await db.execute(select(Project).where(Project.name == data.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="项目名称已存在")

    # 检查 Embedding 厂商是否已配置
    result = await db.execute(
        select(ProviderConfig).where(ProviderConfig.provider == data.embedding_provider)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Embedding 厂商 {data.embedding_provider} 未配置，请先在模型配置中添加"
        )

    if not is_embedding_supported(data.embedding_provider):
        raise HTTPException(
            status_code=400,
            detail=f"厂商 {data.embedding_provider} 不支持 Embedding API"
        )

    project = Project(
        name=data.name,
        description=data.description,
        embedding_provider=data.embedding_provider,
        embedding_model=data.embedding_model,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    return ProjectResponse.model_validate(project)


@router.get("/projects", response_model=ProjectListResponse)
async def get_projects(db: AsyncSession = Depends(get_db)):
    """获取项目列表"""
    count_result = await db.execute(select(func.count(Project.id)))
    total = count_result.scalar()

    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    projects = result.scalars().all()

    return ProjectListResponse(
        total=total,
        projects=[ProjectResponse.model_validate(p) for p in projects],
    )


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    """获取项目详情"""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return ProjectResponse.model_validate(project)


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新项目"""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 检查名称是否重复（排除自身）
    if data.name and data.name != project.name:
        result = await db.execute(select(Project).where(Project.name == data.name))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="项目名称已存在")

    # 如果修改了 Embedding 配置且项目已有文档，需要警告
    embedding_changed = (
        (data.embedding_provider and data.embedding_provider != project.embedding_provider)
        or (data.embedding_model and data.embedding_model != project.embedding_model)
    )
    if embedding_changed and project.doc_count > 0:
        raise HTTPException(
            status_code=400,
            detail="项目已有文档，修改 Embedding 配置会导致已有向量失效。请先删除所有文档后再修改。"
        )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)
    return ProjectResponse.model_validate(project)


@router.delete("/projects/{project_id}")
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)):
    """删除项目（同时删除 ChromaDB collection 和所有文件）"""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 删除 ChromaDB collection
    _kb_service.delete_collection(project_id)

    # 删除关联文档的本地文件
    result = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.project_id == project_id)
    )
    docs = result.scalars().all()
    for doc in docs:
        if doc.local_file_path:
            p = Path(doc.local_file_path)
            if p.exists():
                p.unlink(missing_ok=True)

    await db.delete(project)
    await db.commit()
    return {"message": "项目已删除"}


# ========== 文档管理 ==========

@router.post("/projects/{project_id}/documents", response_model=KnowledgeDocumentResponse)
async def upload_document(
    project_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """上传文档到项目知识库"""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 检查文件类型
    allowed_types = {".pdf", ".doc", ".docx", ".txt", ".md"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_types:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")

    content = await file.read()
    if len(content) > settings.max_file_size:
        raise HTTPException(status_code=400, detail="文件大小超过限制")

    # 保存文件
    upload_dir = Path(settings.upload_dir) / "knowledge"
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = f"{uuid.uuid4()}{ext}"
    file_path = upload_dir / safe_filename

    with open(file_path, "wb") as f:
        f.write(content)

    # 创建文档记录
    doc = KnowledgeDocument(
        project_id=project_id,
        original_filename=file.filename,
        local_file_path=str(file_path),
        file_size=len(content),
        status="processing",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # 后台异步处理：解析 -> 分块 -> 向量化
    background_tasks.add_task(
        _process_document,
        doc.id,
        project_id,
        str(file_path),
        file.filename,
        project.embedding_provider,
        project.embedding_model,
    )

    return KnowledgeDocumentResponse.model_validate(doc)


async def _process_document(
    doc_id: int,
    project_id: int,
    file_path: str,
    filename: str,
    embedding_provider: str,
    embedding_model: str,
):
    """后台处理文档：解析 -> 分块 -> 向量化 -> 存入 ChromaDB"""
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        doc = await db.get(KnowledgeDocument, doc_id)
        if not doc:
            return

        try:
            # 获取厂商 API 配置
            result = await db.execute(
                select(ProviderConfig).where(ProviderConfig.provider == embedding_provider)
            )
            provider_config = result.scalar_one_or_none()
            if not provider_config:
                raise ValueError(f"Embedding 厂商 {embedding_provider} 配置不存在")

            # 创建 Embeddings 实例
            embeddings = create_embeddings(
                provider=embedding_provider,
                api_key=provider_config.api_key,
                base_url=provider_config.base_url,
                model=embedding_model,
            )

            # 在线程池中执行（包含同步的文档解析和 Embedding 计算）
            chunk_count = await asyncio.to_thread(
                _kb_service.add_document,
                project_id,
                file_path,
                doc_id,
                filename,
                embeddings,
            )

            doc.chunk_count = chunk_count
            doc.status = "ready"

            # 更新项目文档计数
            project = await db.get(Project, project_id)
            if project:
                project.doc_count = (project.doc_count or 0) + 1

            await db.commit()

        except Exception as e:
            doc.status = "failed"
            doc.error_message = str(e)
            await db.commit()


@router.get("/projects/{project_id}/documents", response_model=list[KnowledgeDocumentResponse])
async def get_documents(project_id: int, db: AsyncSession = Depends(get_db)):
    """获取项目的文档列表"""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    result = await db.execute(
        select(KnowledgeDocument)
        .where(KnowledgeDocument.project_id == project_id)
        .order_by(KnowledgeDocument.created_at.desc())
    )
    docs = result.scalars().all()
    return [KnowledgeDocumentResponse.model_validate(d) for d in docs]


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    """删除知识库文档"""
    doc = await db.get(KnowledgeDocument, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    project_id = doc.project_id

    # 从 ChromaDB 删除
    _kb_service.remove_document(project_id, doc_id)

    # 删除本地文件
    if doc.local_file_path:
        p = Path(doc.local_file_path)
        if p.exists():
            p.unlink(missing_ok=True)

    # 更新项目文档计数
    project = await db.get(Project, project_id)
    if project and doc.status == "ready":
        project.doc_count = max(0, (project.doc_count or 0) - 1)

    await db.delete(doc)
    await db.commit()
    return {"message": "文档已删除"}


# ========== 检索 ==========

@router.post("/projects/{project_id}/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    project_id: int,
    data: KnowledgeSearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """检索项目知识库"""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 获取厂商配置
    result = await db.execute(
        select(ProviderConfig).where(ProviderConfig.provider == project.embedding_provider)
    )
    provider_config = result.scalar_one_or_none()
    if not provider_config:
        raise HTTPException(status_code=400, detail="Embedding 厂商配置不存在")

    embeddings = create_embeddings(
        provider=project.embedding_provider,
        api_key=provider_config.api_key,
        base_url=provider_config.base_url,
        model=project.embedding_model,
    )

    # 在线程池中执行检索
    results = await asyncio.to_thread(
        _kb_service.search,
        project_id,
        data.query,
        embeddings,
        data.top_k,
    )

    return KnowledgeSearchResponse(
        results=[
            KnowledgeSearchResult(
                content=r["content"],
                metadata=r["metadata"],
                distance=r["distance"],
            )
            for r in results
        ]
    )
