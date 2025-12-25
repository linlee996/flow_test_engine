"""任务模型 - 用例生成任务"""
from datetime import datetime
from enum import IntEnum
from typing import Optional
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class TaskStatus(IntEnum):
    RUNNING = 0      # 运行中
    CLARIFYING = 1   # 等待澄清
    FINISHED = 2     # 完成
    FAILED = 3       # 失败


class Task(Base):
    __tablename__ = "task"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False, comment="原始文件名")
    local_file_path: Mapped[Optional[str]] = mapped_column(String(500), comment="本地上传文件路径")
    status: Mapped[int] = mapped_column(Integer, default=TaskStatus.RUNNING, comment="任务状态")

    # LangGraph 相关
    thread_id: Mapped[Optional[str]] = mapped_column(String(255), comment="LangGraph线程ID")

    # 输出文件
    output_excel: Mapped[Optional[str]] = mapped_column(String(500), comment="输出Excel文件路径")
    output_summary: Mapped[Optional[str]] = mapped_column(String(500), comment="输出总结MD文件路径")
    download_filename: Mapped[Optional[str]] = mapped_column(String(255), comment="下载文件名")

    # 澄清相关
    clarification_message: Mapped[Optional[str]] = mapped_column(Text, comment="待澄清问题")

    # 错误信息
    error_message: Mapped[Optional[str]] = mapped_column(Text, comment="错误信息")

    # 时间戳
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="完成时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
