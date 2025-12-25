# Flow Test Engine - Python Backend

基于 LangGraph + Docling 的智能测试用例生成引擎。

## 技术栈

- **FastAPI** - Web 框架
- **LangGraph** - AI 工作流编排
- **Docling** - 文档解析（PDF/DOCX/TXT/MD）
- **SQLAlchemy** - ORM
- **SQLite** - 数据库

## 项目结构

```
backend/
├── app/
│   ├── api/           # API 路由
│   │   ├── auth.py    # 认证接口
│   │   ├── task.py    # 任务接口
│   │   └── template.py # 模板接口
│   ├── core/          # 核心模块
│   │   ├── config.py  # 配置管理
│   │   ├── database.py # 数据库连接
│   │   └── security.py # JWT/密码
│   ├── models/        # 数据模型
│   ├── schemas/       # Pydantic Schema
│   ├── services/      # 业务服务
│   │   ├── document_parser.py  # Docling 文档解析
│   │   ├── case_generator.py   # LangGraph 工作流
│   │   └── result_extractor.py # 结果提取
│   └── main.py        # 入口
├── data/              # SQLite 数据库
├── uploads/           # 上传文件
├── outputs/           # 输出文件
└── pyproject.toml     # 依赖配置
```

## 快速开始

### 1. 安装依赖

```bash
cd backend
uv sync
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 配置 OpenAI API Key
```

### 3. 启动服务

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

## API 接口

### 认证
- `POST /api/v1/auth/register` - 注册
- `POST /api/v1/auth/login` - 登录

### 任务
- `POST /api/v1/upload` - 上传文件
- `POST /api/v1/task/create` - 创建任务
- `POST /api/v1/task/{id}/clarify` - 提交澄清
- `GET /api/v1/tasks` - 任务列表
- `GET /api/v1/task/{id}/summary` - 获取总结
- `GET /api/v1/download/{id}` - 下载 Excel
- `DELETE /api/v1/tasks/{id}` - 删除任务

### 模板
- `GET /api/v1/templates` - 模板列表
- `POST /api/v1/templates` - 创建模板
- `PUT /api/v1/templates` - 更新模板
- `DELETE /api/v1/templates/{id}` - 删除模板

## 工作流说明

1. **文档上传** → Docling 解析为 Markdown + 提取图片/表格
2. **需求分析** → LLM 分析是否有待澄清问题
3. **人机澄清** → 如有问题，等待用户输入（interrupt）
4. **用例生成** → LLM 生成测试用例
5. **结果提取** → 从 Markdown 提取表格转 Excel + 总结保存 MD
