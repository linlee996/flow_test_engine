"""数据库连接 - SQLAlchemy异步引擎"""
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import get_settings

settings = get_settings()

# 在创建引擎之前确保必要的目录存在
# 从 database_url 解析出数据库目录并创建
_db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
Path(_db_path).parent.mkdir(parents=True, exist_ok=True)
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
Path(settings.output_dir).mkdir(parents=True, exist_ok=True)

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_db():
    """获取数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """初始化数据库表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 初始化系统默认模板
    await _init_default_template()


async def _init_default_template():
    """初始化系统默认模板"""
    from sqlalchemy import select
    from app.models import CaseTemplate

    async with AsyncSessionLocal() as session:
        # 检查是否已存在系统模板
        result = await session.execute(
            select(CaseTemplate).where(CaseTemplate.is_system == True)
        )
        if result.scalar_one_or_none():
            return  # 已存在，跳过

        # 创建系统默认模板
        default_fields = [
            {"name": "用例名称", "description": "简洁明确地描述测试目的"},
            {"name": "所属模块", "description": "采用 `/模块/子模块` 的命名规则（如：`/问题管理/问题列表`）"},
            {"name": "标签", "description": "从 `UI测试`, `功能测试`, `边界测试`, `异常测试`, `场景测试` 中选择"},
            {"name": "前置条件", "description": "执行测试前需要满足的环境和数据条件（包含具体的输入值）"},
            {"name": "步骤描述", "description": "提供详细、清晰、可复现的操作步骤"},
            {"name": "预期结果", "description": "描述明确的验证点和期望输出，确保结果可被验证"},
            {"name": "编辑模式", "description": "默认填充为 TEXT"},
            {"name": "备注", "description": "提供特殊说明或注意事项（如\"需与需求方确认\"、\"基于合理假设\"等）"},
            {"name": "用例等级", "description": "P0 (核心)、P1 (重要)、P2 (次要)、P3 (优化)"},
        ]

        template = CaseTemplate(
            name="标准测试用例模板",
            fields=default_fields,
            is_default=True,
            is_system=True,
        )
        session.add(template)
        await session.commit()
