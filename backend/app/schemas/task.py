"""任务相关 Schema"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class TokenResponse(BaseModel):
    """登录响应"""
    token: str
    username: str


class TaskCreate(BaseModel):
    file_path: str
    original_filename: str
    download_filename: Optional[str] = None
    template_id: Optional[int] = None
    # 使用 provider + model
    provider: str
    model: str
    # 关联知识库项目（可选，启用 RAG 检索）
    project_id: Optional[int] = None



class TaskClarify(BaseModel):
    """澄清响应"""
    clarification_input: str  # 用户输入的澄清信息，或 "忽略待澄清内容，继续生成" 或 "停止生成"


class TaskResponse(BaseModel):
    task_id: int
    original_filename: str
    status: int
    created_at: datetime
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None
    clarification_message: Optional[str] = None
    summary_content: Optional[str] = None
    current_step: Optional[str] = None  # current workflow step (only when running)

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    total: int
    tasks: list[TaskResponse]
