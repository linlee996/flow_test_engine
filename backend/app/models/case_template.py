"""用例模板模型"""
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class CaseTemplate(Base):
    __tablename__ = "case_template"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="模板名称")
    fields: Mapped[list] = mapped_column(JSON, nullable=False, comment="字段列表 [{'name': '字段名', 'description': '字段描述'}]")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否默认模板")
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否系统模板")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
