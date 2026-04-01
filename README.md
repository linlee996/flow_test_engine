# Flow Test Engine

基于 FastAPI + LangGraph + React 的智能测试用例生成平台，支持需求文档解析、多厂商模型管理、项目知识库 RAG、人机澄清交互、自定义用例模板，以及 Excel/Markdown 结果输出。

## 核心能力

- 多厂商模型配置与模型列表管理，支持连接测试、拉取模型和手动补充模型
- 支持 `PDF`、`DOC`、`DOCX`、`TXT`、`MD` 需求文档上传与解析
- 基于 4 阶段 LangGraph 工作流生成测试用例，并支持中断后的澄清恢复
- 支持自定义测试用例模板，适配不同测试管理平台的导入字段
- 支持项目知识库和 ChromaDB 向量检索，在生成任务中通过 RAG 注入上下文
- 支持运行中任务停止、总结查看、Excel 下载和历史任务管理
- 提供 React 前端界面，也支持 Docker 一体化部署

## 功能概览

### 多家 LLM 供应商管理

支持为不同厂商单独配置 `API Key`、`Base URL`、模型列表和可用性状态，当前内置厂商包括：

- `openai`
- `gemini`
- `anthropic`
- `deepseek`
- `kimi`
- `openrouter`

![llm_providers.png](assets/llm_providers.png)

### 用例输出模板自定义

支持按字段维度配置测试用例输出模板，生成时可直接绑定模板，满足不同测试平台的导入要求。

![template_customization.png](assets/template_customization.png)

### 文档解析与内容提取

后端当前使用 `PyMuPDF + python-docx` 解析文档：

- PDF 支持正文提取、表格识别、图片抽取
- DOC/DOCX 支持正文提取
- TXT/MD 直接按文本读取

![doc_parsing.png](assets/doc_parsing.png)

### Human-in-the-Loop 澄清交互

工作流会在需求不完整时进入澄清状态，等待用户补充信息后继续生成；运行中的任务也可以主动停止。

![hitl_clarification.png](assets/hitl_clarification.png)

### 测试总结与结果导出

任务完成后会生成测试用例 Excel、测试覆盖总结和完整工作流输出，方便归档和复核。

![aigc_summary.png](assets/aigc_summary.png)

## 技术栈

### 后端

- Python 3.11+
- FastAPI
- LangGraph + LangChain
- PyMuPDF + python-docx
- SQLAlchemy + SQLite
- ChromaDB
- Pandas + OpenPyXL
- uv

### 前端

- React 19 + TypeScript
- Vite
- Axios
- Framer Motion

## 项目结构

```text
flow_test_engine/
├── assets/                     # README 截图资源
├── backend/
│   ├── app/
│   │   ├── api/               # 认证、任务、模板、模型配置、知识库接口
│   │   ├── core/              # 配置、数据库、鉴权
│   │   ├── models/            # SQLAlchemy 模型
│   │   ├── schemas/           # Pydantic Schema
│   │   └── services/          # 文档解析、工作流、Embedding、知识库、结果提取
│   ├── config/prompts/        # 4 阶段 Prompt
│   ├── data/                  # SQLite / ChromaDB 数据
│   ├── uploads/               # 上传文件
│   ├── outputs/               # Excel、总结、完整输出、中间解析结果
│   ├── .env.example
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/        # React 组件
│   │   ├── services/          # 前端 API 封装
│   │   └── App.tsx
│   └── package.json
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 快速开始

### 方式一：Docker 部署

环境要求：

- Docker 20.10+
- Docker Compose 2.0+

启动：

```bash
docker-compose up -d
```

查看日志：

```bash
docker-compose logs -f
```

停止服务：

```bash
docker-compose down
```

访问地址：

- 应用首页：`http://localhost:8080`
- 接口文档：`http://localhost:8080/docs`
- 健康检查：`http://localhost:8080/health`

默认管理员账号：

- 用户名：`admin`
- 密码：`admin`

说明：

- Docker 镜像默认从 `ghcr.io/linlee996/flow_test_engine:latest` 拉取
- 持久化数据会挂载到仓库根目录下的 `./flow_test_engine/data`、`./flow_test_engine/uploads`、`./flow_test_engine/outputs`、`./flow_test_engine/logs`

### 方式二：本地开发

环境要求：

- Python 3.11+
- Node.js 20+
- uv

启动后端：

```bash
cd backend
uv sync
cp .env.example .env
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

启动前端：

```bash
cd frontend
npm install
npm run dev
```

本地访问地址：

- 后端：`http://localhost:8080`
- 前端开发服务器：`http://localhost:5173`
- 后端接口文档：`http://localhost:8080/docs`

## 任务工作流

1. 上传需求文档并保存原文件
2. 解析正文、表格和图片
3. 如绑定知识库项目，先执行 RAG 检索补充上下文
4. Phase 1：需求分析、结构识别、澄清问题识别
5. 如需澄清，任务进入 `CLARIFYING`
6. Phase 2：生成测试策略与闭环检查
7. Phase 3：输出 Markdown 测试用例表格
8. Phase 4：输出测试覆盖总结
9. 导出 Excel，保存总结和完整工作流输出

运行中的 `current_step` 可能出现以下值：

- `doc_parsing`
- `rag_retrieval`
- `phase1_analysis`
- `phase2_strategy`
- `phase3_generate`
- `phase4_summary`
- `extracting`

## 使用流程

1. 使用内置管理员账号登录系统
2. 在模型配置页配置厂商、测试连接并同步模型列表
3. 按需创建测试用例模板
4. 按需创建知识库项目并上传文档
5. 上传需求文档
6. 创建任务，选择 `provider`、`model`，并可选绑定 `template_id`、`project_id`
7. 处理澄清问题或停止任务
8. 查看总结并下载 Excel

## API 概览

基础信息：

- Base URL：`http://localhost:8080`
- API 前缀：`/api/v1`
- 文档地址：`/docs`

### 认证

- `POST /api/v1/auth/login`

说明：

- 当前没有注册接口
- 登录请求体为 JSON：`{"username": "...", "password": "..."}` 

### 任务

- `POST /api/v1/upload`
- `POST /api/v1/task/create`
- `POST /api/v1/task/{task_id}/clarify`
- `POST /api/v1/task/{task_id}/stop`
- `GET /api/v1/tasks`
- `GET /api/v1/task/{task_id}/summary`
- `GET /api/v1/download/{task_id}`
- `DELETE /api/v1/tasks/{task_id}`

`POST /api/v1/task/create` 关键字段：

- `file_path`
- `original_filename`
- `provider`
- `model`
- `download_filename`
- `template_id`
- `project_id`

### 模板

- `GET /api/v1/templates`
- `POST /api/v1/templates`
- `PUT /api/v1/templates`
- `DELETE /api/v1/templates/{template_id}`

### 模型配置

- `GET /api/v1/llm-configs/provider-list`
- `GET /api/v1/llm-configs/provider-configs/{provider}`
- `PUT /api/v1/llm-configs/provider-configs/{provider}`
- `POST /api/v1/llm-configs/provider-configs/{provider}/models/{model_name}/test`
- `POST /api/v1/llm-configs/provider-configs/{provider}/fetch-models`
- `POST /api/v1/llm-configs/provider-configs/{provider}/models`
- `DELETE /api/v1/llm-configs/provider-configs/{provider}/models/{model_name}`
- `GET /api/v1/llm-configs/model-groups`

### 知识库

- `GET /api/v1/knowledge/embedding-providers`
- `POST /api/v1/knowledge/projects`
- `GET /api/v1/knowledge/projects`
- `GET /api/v1/knowledge/projects/{project_id}`
- `PUT /api/v1/knowledge/projects/{project_id}`
- `DELETE /api/v1/knowledge/projects/{project_id}`
- `POST /api/v1/knowledge/projects/{project_id}/documents`
- `GET /api/v1/knowledge/projects/{project_id}/documents`
- `DELETE /api/v1/knowledge/documents/{doc_id}`
- `POST /api/v1/knowledge/projects/{project_id}/search`

## 配置说明

`backend/.env.example` 当前包含基础启动配置：

- `DEBUG`
- `HOST`
- `PORT`
- `JWT_SECRET`
- `MAX_FILE_SIZE`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`

此外，后端也支持通过环境变量覆盖以下运行参数：

- `DATABASE_URL`
- `UPLOAD_DIR`
- `OUTPUT_DIR`
- `CHROMA_DIR`
- `DEMO_MODE`

## 输出产物

任务完成后，默认会在 `backend/outputs/` 下生成：

- `*_parsed_document.md`：解析后的文档内容，便于排查解析问题
- `*_full_output.md`：完整工作流输出
- `*_summary.md`：测试覆盖总结
- `*.xlsx`：测试用例 Excel 文件

## 说明

- 默认最大上传大小为 `50MB`
- 支持上传格式：`PDF`、`DOC`、`DOCX`、`TXT`、`MD`
- Docker 镜像中会将前端构建产物挂载为后端静态资源，由 `http://localhost:8080` 统一提供
