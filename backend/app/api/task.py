"""任务管理 API - 核心业务逻辑"""
import os
import uuid
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from shutil import rmtree

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core import get_db, get_settings
from app.models import Task, TaskStatus, CaseTemplate, ProviderConfig, Project
from app.schemas import TaskCreate, TaskClarify, TaskResponse, TaskListResponse
from app.services import DocumentParser, CaseGeneratorWorkflow, ResultExtractor
from app.services.knowledge_service import KnowledgeBaseService
from app.services.embedding_service import create_embeddings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

_parser = DocumentParser()
_extractor = ResultExtractor()
_kb_service = KnowledgeBaseService()
# 存储每个任务的工作流实例（按 thread_id）
_workflows: dict[str, CaseGeneratorWorkflow] = {}
# 内存中存储运行中任务的当前步骤（task_id -> step_key）
_task_progress: dict[int, str] = {}
# 已取消的任务集合（on_step 回调中检查并抛异常中断工作流）
_cancelled_tasks: set[int] = set()


class TaskCancelledException(Exception):
    """任务被用户取消"""
    pass


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """上传需求文档"""
    allowed_types = {".pdf", ".doc", ".docx", ".txt", ".md"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_types:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")

    content = await file.read()
    if len(content) > settings.max_file_size:
        raise HTTPException(status_code=400, detail="文件大小超过限制")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_filename = f"{uuid.uuid4()}{ext}"
    file_path = upload_dir / safe_filename

    with open(file_path, "wb") as f:
        f.write(content)

    return {"file_path": str(file_path), "original_filename": file.filename}


@router.post("/task/create", response_model=TaskResponse)
async def create_task(
    data: TaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """创建用例生成任务"""
    # 查找厂商配置
    result = await db.execute(
        select(ProviderConfig).where(ProviderConfig.provider == data.provider)
    )
    provider_config = result.scalar_one_or_none()
    if not provider_config:
        raise HTTPException(status_code=400, detail=f"请先配置 {data.provider} 厂商")
    
    provider = data.provider
    base_url = provider_config.base_url
    api_key = provider_config.api_key
    model = data.model

    # 获取模板并构建完整 prompt
    template_prompt = None
    if data.template_id:
        result = await db.execute(
            select(CaseTemplate).where(CaseTemplate.id == data.template_id)
        )
        template = result.scalar_one_or_none()
        if template:
            template_prompt = _build_prompt_with_template(template.fields)

    # 创建任务记录
    task = Task(
        original_filename=data.original_filename,
        local_file_path=data.file_path,
        download_filename=data.download_filename or data.original_filename,
        status=TaskStatus.RUNNING,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # 后台执行工作流
    background_tasks.add_task(
        _run_workflow,
        task.id,
        data.file_path,
        template_prompt,
        provider,
        base_url,
        api_key,
        model,
        data.project_id,
    )

    return _task_to_response(task)


def _save_parsed_document(task_id: int, parsed_doc) -> None:
    """Save parsed document markdown to outputs for debugging/verification."""
    try:
        output_dir = Path(settings.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        parsed_path = output_dir / f"{task_id}_parsed_document.md"

        content_parts = [parsed_doc.markdown]

        if parsed_doc.tables:
            content_parts.append("\n\n---\n\n## Extracted Tables\n")
            for i, t in enumerate(parsed_doc.tables, 1):
                content_parts.append(f"\n### {t.get('caption', f'Table {i}')}\n\n{t['markdown']}\n")

        if parsed_doc.images:
            content_parts.append(f"\n\n---\n\n## Extracted Images: {len(parsed_doc.images)} image(s)\n")
            for i, img in enumerate(parsed_doc.images, 1):
                caption = img.get("caption", f"Image {i}")
                has_data = "yes" if img.get("base64") else "no"
                content_parts.append(f"\n- {caption} (base64 data: {has_data})\n")

        with open(parsed_path, "w", encoding="utf-8") as f:
            f.write("".join(content_parts))

        logger.info(f"Parsed document saved: {parsed_path}")
    except Exception as e:
        logger.warning(f"Failed to save parsed document for task {task_id}: {e}")


async def _run_workflow(
    task_id: int,
    file_path: str,
    template_prompt: str | None,
    provider: str,
    base_url: str,
    api_key: str,
    model: str,
    project_id: int | None = None,
):
    """后台执行工作流"""
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        task = await db.get(Task, task_id)
        if not task:
            return

        try:
            # 取消检查辅助函数
            def _check_cancelled():
                if task_id in _cancelled_tasks:
                    raise TaskCancelledException("用户取消任务")

            # 解析文档 - 在线程池中运行避免阻塞事件循环
            _task_progress[task_id] = "doc_parsing"
            parsed_doc = await asyncio.to_thread(_parser.parse, file_path)
            _check_cancelled()

            # Save parsed document to outputs for debugging/verification
            _save_parsed_document(task_id, parsed_doc)

            # RAG 检索：如果关联了项目知识库，从中检索相关上下文
            rag_context = ""
            if project_id:
                _task_progress[task_id] = "rag_retrieval"
                rag_context = await _retrieve_rag_context(
                    project_id, parsed_doc.markdown, db,
                    provider, base_url, api_key, model,
                )
                _check_cancelled()

            # 创建工作流实例（使用动态 LLM 配置）
            def on_step(step: str):
                if task_id in _cancelled_tasks:
                    raise TaskCancelledException("用户取消任务")
                _task_progress[task_id] = step

            workflow = CaseGeneratorWorkflow(
                api_key=api_key,
                base_url=base_url,
                model=model,
                provider=provider,
                on_step=on_step,
            )

            # 启动工作流 - 在线程池中运行避免阻塞事件循环
            _task_progress[task_id] = "phase1_analysis"
            thread_id, result = await asyncio.to_thread(
                workflow.start, parsed_doc, template_prompt, rag_context
            )
            task.thread_id = thread_id

            # 保存工作流实例
            _workflows[thread_id] = workflow

            # 检查是否需要澄清
            if result.get("has_clarification"):
                task.status = TaskStatus.CLARIFYING
                task.clarification_message = result.get("clarification_questions", "")
                _task_progress.pop(task_id, None)
            elif result.get("report_markdown"):
                _task_progress[task_id] = "extracting"
                await _finalize_task(task, result, db)
                # 清理工作流实例和进度
                _workflows.pop(thread_id, None)
                _task_progress.pop(task_id, None)
            else:
                task.status = TaskStatus.FAILED
                task.error_message = "工作流未返回有效结果"
                _workflows.pop(thread_id, None)
                _task_progress.pop(task_id, None)

            await db.commit()

        except TaskCancelledException:
            task.status = TaskStatus.FAILED
            task.error_message = "用户取消任务"
            _task_progress.pop(task_id, None)
            _cancelled_tasks.discard(task_id)
            if task.thread_id:
                _workflows.pop(task.thread_id, None)
            await db.commit()
            logger.info(f"Task {task_id} cancelled by user")

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            _task_progress.pop(task_id, None)
            _cancelled_tasks.discard(task_id)
            await db.commit()


async def _finalize_task(task: Task, result: dict, db: AsyncSession):
    """完成任务，提取结果（支持分阶段输出）"""
    try:
        excel_path, summary_path, _ = _extractor.extract_and_save(
            report_markdown=result.get("report_markdown", ""),
            task_id=task.id,
            filename=task.download_filename or task.original_filename,
            cases_markdown=result.get("cases_markdown", ""),
            summary_text=result.get("summary_result", ""),
        )
        task.output_excel = excel_path
        task.output_summary = summary_path
        task.status = TaskStatus.FINISHED
        task.finished_at = datetime.utcnow()
    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error_message = f"结果提取失败: {e}"


@router.post("/task/{task_id}/stop", response_model=TaskResponse)
async def stop_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """停止运行中的任务"""
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status not in (TaskStatus.RUNNING, TaskStatus.CLARIFYING):
        raise HTTPException(status_code=400, detail="任务不在运行中，无法停止")

    # 如果是澄清状态，直接标记失败
    if task.status == TaskStatus.CLARIFYING:
        task.status = TaskStatus.FAILED
        task.error_message = "用户取消任务"
        task.clarification_message = None
        if task.thread_id:
            _workflows.pop(task.thread_id, None)
        _task_progress.pop(task_id, None)
        await db.commit()
        return _task_to_response(task)

    # 运行中：设置取消标记，后台线程会在下一个 on_step 检查点抛异常
    _cancelled_tasks.add(task_id)
    logger.info(f"Task {task_id} stop requested, will cancel at next checkpoint")

    return _task_to_response(task)


@router.post("/task/{task_id}/clarify", response_model=TaskResponse)
async def clarify_task(
    task_id: int,
    data: TaskClarify,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """提交澄清信息"""
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != TaskStatus.CLARIFYING:
        raise HTTPException(status_code=400, detail="任务不在澄清状态")

    if data.clarification_input == "停止生成":
        task.status = TaskStatus.FAILED
        task.error_message = "用户停止生成"
        _workflows.pop(task.thread_id, None)
        await db.commit()
        return _task_to_response(task)

    task.status = TaskStatus.RUNNING
    task.clarification_message = None
    await db.commit()

    background_tasks.add_task(_resume_workflow, task.id, data.clarification_input)

    return _task_to_response(task)


async def _resume_workflow(task_id: int, clarification_input: str):
    """恢复工作流"""
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        task = await db.get(Task, task_id)
        if not task or not task.thread_id:
            return

        workflow = _workflows.get(task.thread_id)
        if not workflow:
            task.status = TaskStatus.FAILED
            task.error_message = "工作流实例丢失，请重新创建任务"
            await db.commit()
            return

        try:
            # 在线程池中运行避免阻塞事件循环
            _task_progress[task_id] = "phase2_strategy"
            result = await asyncio.to_thread(workflow.resume, task.thread_id, clarification_input)

            if result.get("is_stopped"):
                task.status = TaskStatus.FAILED
                task.error_message = "用户停止生成"
                _workflows.pop(task.thread_id, None)
                _task_progress.pop(task_id, None)
            elif result.get("has_clarification"):
                task.status = TaskStatus.CLARIFYING
                task.clarification_message = result.get("clarification_questions", "")
                _task_progress.pop(task_id, None)
            elif result.get("report_markdown"):
                _task_progress[task_id] = "extracting"
                await _finalize_task(task, result, db)
                _workflows.pop(task.thread_id, None)
                _task_progress.pop(task_id, None)
            else:
                task.status = TaskStatus.FAILED
                task.error_message = "工作流未返回有效结果"
                _workflows.pop(task.thread_id, None)
                _task_progress.pop(task_id, None)

            await db.commit()

        except TaskCancelledException:
            task.status = TaskStatus.FAILED
            task.error_message = "用户取消任务"
            _task_progress.pop(task_id, None)
            _cancelled_tasks.discard(task_id)
            if task.thread_id:
                _workflows.pop(task.thread_id, None)
            await db.commit()
            logger.info(f"Resumed task {task_id} cancelled by user")

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            _workflows.pop(task.thread_id, None)
            _task_progress.pop(task_id, None)
            _cancelled_tasks.discard(task_id)
            await db.commit()


@router.get("/tasks", response_model=TaskListResponse)
async def get_tasks(
    page: int = 1,
    page_size: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """获取任务列表"""
    count_result = await db.execute(select(func.count(Task.id)))
    total = count_result.scalar()

    result = await db.execute(
        select(Task).order_by(Task.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    tasks = result.scalars().all()

    return TaskListResponse(total=total, tasks=[_task_to_response(t) for t in tasks])


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除任务（运行中/澄清中的任务不允许删除）"""
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status in (TaskStatus.RUNNING, TaskStatus.CLARIFYING):
        raise HTTPException(
            status_code=400,
            detail="任务正在运行中，请先停止任务再删除",
        )

    # 清理工作流实例
    if task.thread_id:
        _workflows.pop(task.thread_id, None)

    for path in [task.local_file_path, task.output_excel, task.output_summary]:
        if path and isinstance(path, str):
            p = Path(path)
            if p.exists():
                try:
                    if p.is_file():
                        p.unlink()
                    elif p.is_dir():
                        rmtree(p)
                except Exception:
                    pass

    await db.delete(task)
    await db.commit()
    return {"message": "删除成功"}


@router.get("/download/{task_id}")
async def download_file(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """下载生成的 Excel 文件"""
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != TaskStatus.FINISHED or not task.output_excel:
        raise HTTPException(status_code=400, detail="任务未完成或无输出文件")

    if not os.path.exists(task.output_excel):
        raise HTTPException(status_code=404, detail="文件不存在")

    download_name = f"{task.download_filename or 'test_cases'}.xlsx"

    return FileResponse(
        task.output_excel,
        filename=download_name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/task/{task_id}/summary")
async def get_summary(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取任务总结内容"""
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if not task.output_summary:
        raise HTTPException(status_code=400, detail="无总结内容")

    content = _extractor.read_summary(task.output_summary)
    if not content:
        raise HTTPException(status_code=404, detail="总结文件不存在")

    return {"summary": content}


def _task_to_response(task: Task) -> TaskResponse:
    """转换任务为响应格式"""
    summary_content = None
    if task.output_summary:
        summary_content = _extractor.read_summary(task.output_summary)

    # running state: read current step from in-memory progress dict
    current_step = None
    if task.status == TaskStatus.RUNNING:
        current_step = _task_progress.get(task.id)

    return TaskResponse(
        task_id=task.id,
        original_filename=task.original_filename,
        status=task.status,
        created_at=task.created_at,
        finished_at=task.finished_at,
        error_message=task.error_message,
        clarification_message=task.clarification_message,
        summary_content=summary_content,
        current_step=current_step,
    )


def _build_prompt_with_template(fields: list[dict]) -> str:
    """
    根据模板字段构建 Phase3 的自定义 prompt。

    在 4 阶段工作流中，自定义模板只影响 Phase3（生成测试用例）的输出格式部分。
    读取 phase3_generate.md 并替换其中的 3.3 节字段定义。
    """
    import re
    from pathlib import Path

    # 读取 phase3 的默认 prompt
    phase3_file = Path(__file__).parent.parent.parent / "config" / "prompts" / "phase3_generate.md"
    if not phase3_file.exists():
        raise FileNotFoundError(f"Phase3 prompt not found: {phase3_file}")

    prompt_content = phase3_file.read_text(encoding="utf-8")

    # 格式化字段列表
    fields_text = "每个测试用例必须且仅包含以下字段：\n\n"
    for i, field in enumerate(fields, 1):
        fields_text += f"{i}. **{field['name']}**：{field['description']}\n"

    # 替换 3.3 节内容
    pattern = r"(### 3\.3 测试用例输出格式\n\n).*?(\n\n\*\*特殊说明：\*\*)"
    replacement = r"\1" + fields_text + r"\2"

    new_prompt = re.sub(pattern, replacement, prompt_content, flags=re.DOTALL)

    return new_prompt


async def _retrieve_rag_context(
    project_id: int,
    document_content: str,
    db: AsyncSession,
    provider: str,
    base_url: str,
    api_key: str,
    model: str,
) -> str:
    """
    从项目知识库检索与需求文档相关的上下文。

    策略：先用 LLM 从需求文档中提取功能模块和主题关键词，
    再按模块逐个检索向量库，最后去重合并成完整的 RAG context。
    避免直接拿大段原文查询导致语义模糊、断章取义。
    """
    try:
        project = await db.get(Project, project_id)
        if not project or project.doc_count == 0:
            return ""

        # 获取 Embedding 厂商配置
        result = await db.execute(
            select(ProviderConfig).where(ProviderConfig.provider == project.embedding_provider)
        )
        provider_config = result.scalar_one_or_none()
        if not provider_config:
            logger.warning(f"Embedding provider {project.embedding_provider} not configured")
            return ""

        embeddings = create_embeddings(
            provider=project.embedding_provider,
            api_key=provider_config.api_key,
            base_url=provider_config.base_url,
            model=project.embedding_model,
        )

        # ========== 第 1 步：用轻量 LLM 提取需求文档中的功能模块主题 ==========
        from app.services.case_generator import create_llm
        from langchain_core.messages import HumanMessage, SystemMessage

        # 各厂商对应的轻量小模型（只做主题提取，不需要大模型）
        _LITE_MODELS = {
            "openai": "gpt-4o-mini",
            "gemini": "gemini-2.0-flash-lite",
            "anthropic": "claude-3-haiku-20240307",
            "deepseek": "deepseek-chat",       # DeepSeek 本身就便宜
            "kimi": "moonshot-v1-8k",           # 最小上下文窗口的版本
            "openrouter": "google/gemini-2.0-flash-lite",
        }
        lite_model = _LITE_MODELS.get(provider.lower(), model)
        llm = create_llm(provider=provider, api_key=api_key, base_url=base_url, model=lite_model)

        extract_prompt = (
            "你是一个需求分析专家。请分析以下需求文档，提取出所有独立的功能模块或业务主题。\n"
            "每个模块用一句话概括其核心功能和涉及的关键业务概念。\n\n"
            "输出要求：\n"
            "- 每行一个模块主题，格式为纯文本描述\n"
            "- 只输出模块主题列表，不要输出其他内容\n"
            "- 最多提取 10 个模块\n"
            "- 每个主题控制在 50 字以内\n\n"
            "示例输出：\n"
            "用户注册登录模块，包含手机号注册、密码登录、第三方OAuth认证\n"
            "订单管理模块，包含订单创建、支付、退款、状态流转\n"
            "商品库存管理，包含入库、出库、库存预警、盘点\n"
        )

        messages = [
            SystemMessage(content=extract_prompt),
            HumanMessage(content=f"需求文档内容：\n\n{document_content}"),
        ]

        # 在线程池中调用 LLM 提取模块主题
        response = await asyncio.to_thread(llm.invoke, messages)
        topics_text = response.content.strip()

        # 解析模块主题列表（按行分割，过滤空行）
        topics = [
            line.strip().lstrip("0123456789.-、） )")
            for line in topics_text.split("\n")
            if line.strip() and len(line.strip()) > 2
        ]

        if not topics:
            logger.warning("LLM failed to extract topics from document")
            return ""

        logger.info(f"Extracted {len(topics)} topics for RAG retrieval: {topics}")

        # ========== 第 2 步：按模块逐个检索向量库 ==========
        seen_chunk_ids = set()  # 用于去重
        all_results = []
        top_k_per_topic = 3  # 每个主题检索 3 个最相关片段

        for topic in topics:
            results = await asyncio.to_thread(
                _kb_service.search,
                project_id,
                topic,
                embeddings,
                top_k_per_topic,
            )
            for r in results:
                # 用 chunk 内容的 hash 去重（同一片段可能被多个主题命中）
                chunk_key = hash(r["content"])
                if chunk_key not in seen_chunk_ids:
                    seen_chunk_ids.add(chunk_key)
                    all_results.append(r)

        if not all_results:
            return ""

        # ========== 第 3 步：封装最终 RAG context ==========
        context_parts = []
        for i, r in enumerate(all_results, 1):
            source = r["metadata"].get("filename", "未知来源")
            context_parts.append(f"### 参考片段 {i}（来源：{source}）\n\n{r['content']}")

        logger.info(
            f"RAG context assembled: {len(all_results)} unique chunks "
            f"from {len(topics)} topics for project {project_id}"
        )
        return "\n\n---\n\n".join(context_parts)

    except Exception as e:
        logger.warning(f"RAG retrieval failed for project {project_id}: {e}")
        return ""
