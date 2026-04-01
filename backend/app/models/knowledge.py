"""知识库模型 - 项目 + 知识库文档"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Project(Base):
    """项目 - 知识库的容器，每个项目有独立的 ChromaDB collection"""
    __tablename__ = "project"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, comment="项目名称")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="项目描述")

    # Embedding 配置（复用已配置的 LLM 厂商 API）
    embedding_provider: Mapped[str] = mapped_column(String(50), nullable=False, comment="Embedding 厂商标识")
    embedding_model: Mapped[str] = mapped_column(String(200), nullable=False, comment="Embedding 模型名")

    # 冗余统计字段
    doc_count: Mapped[int] = mapped_column(Integer, default=0, comment="文档数量")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联文档列表
    documents: Mapped[list["KnowledgeDocument"]] = relationship(
        "KnowledgeDocument", back_populates="project", cascade="all, delete-orphan"
    )


class KnowledgeDocument(Base):
    """知识库文档 - 上传到项目知识库中的文档"""
    __tablename__ = "knowledge_document"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False, comment="原始文件名")
    local_file_path: Mapped[Optional[str]] = mapped_column(String(500), comment="本地文件路径")
    file_size: Mapped[int] = mapped_column(Integer, default=0, comment="文件大小(字节)")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, comment="分块数量")
    status: Mapped[str] = mapped_column(String(20), default="processing", comment="状态: processing/ready/failed")
    error_message: Mapped[Optional[str]] = mapped_column(Text, comment="错误信息")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关联项目
    project: Mapped["Project"] = relationship("Project", back_populates="documents")
