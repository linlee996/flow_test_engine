"""任务管理 API - 核心业务逻辑"""
import os
import uuid
import asyncio
from pathlib import Path
from datetime import datetime
from shutil import rmtree

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core import get_db, get_settings
from app.models import Task, TaskStatus, CaseTemplate, ProviderConfig
from app.schemas import TaskCreate, TaskClarify, TaskResponse, TaskListResponse
from app.services import DocumentParser, CaseGeneratorWorkflow, ResultExtractor

router = APIRouter()
settings = get_settings()

_parser = DocumentParser()
_extractor = ResultExtractor()
# 存储每个任务的工作流实例（按 thread_id）
_workflows: dict[str, CaseGeneratorWorkflow] = {}


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
        data.advanced_parsing,
    )

    return _task_to_response(task)


async def _run_workflow(
    task_id: int,
    file_path: str,
    template_prompt: str | None,
    provider: str,
    base_url: str,
    api_key: str,
    model: str,
    advanced_parsing: bool = False,
):
    """后台执行工作流"""
    import asyncio
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        task = await db.get(Task, task_id)
        if not task:
            return

        try:
            # 解析文档 - 在线程池中运行避免阻塞事件循环
            parsed_doc = await asyncio.to_thread(_parser.parse, file_path, advanced_parsing)

            # 创建工作流实例（使用动态 LLM 配置）
            workflow = CaseGeneratorWorkflow(
                api_key=api_key,
                base_url=base_url,
                model=model,
                provider=provider,
            )

            # 启动工作流 - 在线程池中运行避免阻塞事件循环
            thread_id, result = await asyncio.to_thread(workflow.start, parsed_doc, template_prompt)
            task.thread_id = thread_id

            # 保存工作流实例
            _workflows[thread_id] = workflow

            # 检查是否需要澄清
            if result.get("has_clarification"):
                task.status = TaskStatus.CLARIFYING
                task.clarification_message = result.get("clarification_questions", "")
            elif result.get("report_markdown"):
                await _finalize_task(task, result["report_markdown"], db)
                # 清理工作流实例
                _workflows.pop(thread_id, None)
            else:
                task.status = TaskStatus.FAILED
                task.error_message = "工作流未返回有效结果"
                _workflows.pop(thread_id, None)

            await db.commit()

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            await db.commit()


async def _finalize_task(task: Task, report_markdown: str, db: AsyncSession):
    """完成任务，提取结果"""
    try:
        excel_path, summary_path, _ = _extractor.extract_and_save(
            report_markdown,
            task.id,
            task.download_filename or task.original_filename,
        )
        task.output_excel = excel_path
        task.output_summary = summary_path
        task.status = TaskStatus.FINISHED
        task.finished_at = datetime.utcnow()
    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error_message = f"结果提取失败: {e}"


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
            result = await asyncio.to_thread(workflow.resume, task.thread_id, clarification_input)

            if result.get("is_stopped"):
                task.status = TaskStatus.FAILED
                task.error_message = "用户停止生成"
                _workflows.pop(task.thread_id, None)
            elif result.get("has_clarification"):
                task.status = TaskStatus.CLARIFYING
                task.clarification_message = result.get("clarification_questions", "")
            elif result.get("report_markdown"):
                await _finalize_task(task, result["report_markdown"], db)
                _workflows.pop(task.thread_id, None)
            else:
                task.status = TaskStatus.FAILED
                task.error_message = "工作流未返回有效结果"
                _workflows.pop(task.thread_id, None)

            await db.commit()

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            _workflows.pop(task.thread_id, None)
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
    """删除任务"""
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

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

    return TaskResponse(
        task_id=task.id,
        original_filename=task.original_filename,
        status=task.status,
        created_at=task.created_at,
        finished_at=task.finished_at,
        error_message=task.error_message,
        clarification_message=task.clarification_message,
        summary_content=summary_content,
    )


def _build_prompt_with_template(fields: list[dict]) -> str:
    """
    根据模板字段构建完整的 prompt
    将字段列表格式化后替换 prompt.md 中的 3.3 节内容
    """
    import re
    from pathlib import Path

    # 读取 prompt.md
    prompt_file = Path(__file__).parent.parent.parent / "config" / "prompt.md"
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

    prompt_content = prompt_file.read_text(encoding="utf-8")

    # 格式化字段列表
    fields_text = "每个测试用例必须且仅包含以下字段：\n\n"
    for i, field in enumerate(fields, 1):
        fields_text += f"{i}. **{field['name']}**：{field['description']}\n"

    # 替换 3.3 节内容（从 "### 3.3 测试用例输出格式" 到下一个 "###" 或 "**特殊说明：**"）
    pattern = r"(### 3\.3 测试用例输出格式\n\n).*?(\n\n\*\*特殊说明：\*\*)"
    replacement = r"\1" + fields_text + r"\2"

    new_prompt = re.sub(pattern, replacement, prompt_content, flags=re.DOTALL)

    return new_prompt
