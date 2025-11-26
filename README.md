# Flow Test Engine

基于 Langflow 工作流的智能测试用例生成引擎，支持从需求文档自动生成测试用例。

##  特性

-  **AI 驱动**：集成 Langflow 工作流，智能解析需求文档
-  **多格式支持**：支持 PDF、Word、Excel 等多种文档格式
-  **现代化界面**：基于 React + TypeScript 的响应式 Web 界面
-  **任务管理**：完整的任务创建、查询、删除功能
-  **实时状态**：任务执行状态实时更新
-  **轻量存储**：使用 SQLite 数据库，无需额外安装

## 技术栈

### 后端
- **语言**：Go 1.24.4+
- **框架**：Gin Web Framework
- **数据库**：SQLite (GORM)
- **日志**：Zap
- **配置**：Viper

### 前端
- **框架**：React 19 + TypeScript
- **构建工具**：Vite
- **UI 组件**：自定义组件库
- **动画**：Framer Motion
- **HTTP 客户端**：Axios

##  项目结构

```
flow_test_engine/
├── cmd/
│   └── api/                              # 服务启动入口
├── config/
│   ├── config.yaml                       # 配置文件
│   ├── prompt.md                         # AI 提示词模板
│   └── Test Case Generation Flow.json   # Langflow 工作流文件（需导入）
├── internal/                             # 内部模块
│   ├── api/                              # HTTP 接口层
│   ├── service/                          # 业务逻辑层
│   ├── repo/                             # 数据访问层
│   ├── assemble/                         # DTO 转换层
│   ├── dto/                              # 数据传输对象
│   ├── middleware/                       # 中间件
│   └── errcodes/                         # 错误码定义
├── pkg/                                  # 公共包
│   ├── common/                           # 配置管理
│   └── infrastructure/                   # 基础设施（数据库、日志）
├── utils/                                # 工具函数
├── frontend/                             # 前端项目
│   ├── src/
│   │   ├── components/                   # React 组件
│   │   ├── services/                     # API 服务
│   │   └── App.tsx                       # 主应用
│   └── package.json
├── data/                                 # SQLite 数据库文件
├── uploads/                              # 上传文件目录
├── outputs/                              # 输出文件目录
└── scripts/                              # 脚本文件
```

##  快速开始

### 环境要求

- Go 1.24.4+
- Node.js 18+
- Langflow 服务（用于 AI 工作流）
- OpenAI 兼容的 LLM API（如 OpenAI、Azure OpenAI、本地模型等）或其他 Langflow 支持的模型

### 第一步：搭建 Langflow 服务

#### 1.1 安装 Langflow

```bash
# 使用 pip 安装
pip install langflow

# 启动 Langflow 服务
langflow run --host 0.0.0.0 --port 7860
```

访问 `http://localhost:7860` 打开 Langflow 界面。

#### 1.2 导入工作流

1. 在 Langflow 界面中，点击 **Import** 按钮
2. 选择项目中的 `config/Test Case Generation Flow.json` 文件
3. 工作流将自动加载到 Langflow 中

#### 1.3 配置 OpenAI Agent

在导入的工作流中，找到 OpenAI 组件并配置：

1. **Base URL**：填写你的 LLM API 地址
   - OpenAI 官方：`https://api.openai.com/v1`
   - 其他中转 API 模型：`http://api.newapi:8000/v1`

2. **API Key**：填写对应的 API 密钥

3. **Model**：手动输入模型名称
   - OpenAI：`gpt-4`、`gpt-3.5-turbo`
   - 其他：`qwen2.5`、`gemini-3-pro` 等

   > **注意**：由于 Langflow 没有自动获取模型列表的接口，需要手动输入模型名称。前端显示可能存在问题，但不影响正常运行。
   > Base URL 必须添加 /v1 结尾，且不能有多余的斜杠。
   > 如有其他 Langflow 直接支持的厂商 component 组件（如：OpenRouter、Gemini 等），可以直接在 flow 中替换现有 flow 中的 OpenAI 组件。

#### 1.4 获取配置信息

配置完成后，需要获取以下信息：

1. **Langflow API Key**：
   - 点击右上角设置图标
   - 进入 **Settings** → **API Keys**
   - 创建或复制 API Key

2. **工作流 ID (Flow ID)**：
   - 在工作流页面，查看浏览器地址栏
   - URL 格式：`http://localhost:7860/flow/{flow_id}`
   - 复制 `{flow_id}` 部分

3. **组件 ID**：
   - 点击工作流中的各个组件
   - 在组件设置面板中找到组件 ID
   - 需要获取以下三个组件的 ID：
     - **File 组件 ID**：文件输入组件
     - **SaveToFile 组件 ID**：文件保存组件
     - **Prompt 组件 ID**：提示词组件

### 第二步：配置项目

编辑 `config/config.yaml`，填入上一步获取的信息：

```yaml
port: 8080

sqlite:
  db_path: ./data/flow_test.db
  max_open_conns: 1
  max_idle_conns: 1

langflow:
  # Langflow 服务地址
  base_url: http://localhost:7860
  # Langflow API Key（从 Langflow 设置中获取）
  api_key: "sk-xxx..."
  # 工作流 ID（从浏览器地址栏获取）
  flow_id: "2a1626f8-d206-41a7-bf33-3b934262b07d"
  # File 组件 ID
  file_component_id: "File-DeEXB"
  # SaveToFile 组件 ID
  file_save_component_id: "SaveToFile-Qlkl0"
  # Prompt 组件 ID
  prompt_component_id: "Prompt-pX7x9"

file:
  max_file_size: 52428800  # 50MB
  upload_dir: ./uploads
  output_dir: ./outputs
```

### 第三步：启动后端服务

```bash
# 安装依赖
go mod download

# 运行服务
cd cmd/api
go run main.go
```

服务将在 `http://localhost:8080` 启动

### 第四步：启动前端服务

```bash
cd frontend

# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建
npm run build
```

前端开发服务器将在 `http://localhost:5173` 启动

### 第五步：验证服务

```bash
# 健康检查
curl http://localhost:8080/ping

# 预期响应
{"code":0,"message":"pong"}
```

### 完整启动流程总结

1.  **Langflow 服务**：`langflow run --host 0.0.0.0 --port 7860`
2.  **导入工作流**：在 Langflow 中导入 `config/Test Case Generation Flow.json`
3.  **配置 Agent**：设置 OpenAI Base URL、API Key 和 Model
4.  **获取配置**：复制 Langflow API Key、Flow ID 和组件 ID
5.  **更新配置**：填写 `config/config.yaml`
6.  **启动后端**：`cd cmd/api && go run main.go`
7.  **启动前端**：`cd frontend && npm run dev`
8.  **访问应用**：打开 `http://localhost:5173`

## 📖 API 文档

### 基础信息

- **Base URL**: `http://localhost:8080`
- **响应格式**: JSON

### 统一响应结构

```json
{
  "code": 0,           // 0: 成功, 1: 失败
  "message": "操作成功",
  "data": { ... }      // 业务数据
}
```

### 接口列表

#### 1. 健康检查

```http
GET /ping
```

#### 2. 创建任务

```http
POST /api/v1/task/create
Content-Type: multipart/form-data

file: <文件>
```

**响应示例**：
```json
{
  "code": 0,
  "message": "任务创建成功",
  "data": {
    "task_id": "123e4567-e89b-12d3-a456-426614174000"
  }
}
```

#### 3. 查询任务列表

```http
GET /api/v1/task/list?page=1&page_size=10&status=0
```

**查询参数**：
- `page`: 页码（默认 1）
- `page_size`: 每页数量（默认 20，最大 100）
- `status`: 状态筛选（0: 运行中, 1: 完成, 2: 失败）
- `task_id`: 任务 ID 筛选
- `original_filename`: 文件名模糊搜索

**响应示例**：
```json
{
  "code": 0,
  "message": "查询成功",
  "data": {
    "list": [
      {
        "id": 1,
        "task_id": "123e4567-e89b-12d3-a456-426614174000",
        "original_filename": "需求文档.pdf",
        "file_type": "pdf",
        "status": 1,
        "error_message": "",
        "created_at": "2025-11-17 15:00:00",
        "finished_at": "2025-11-17 15:05:00",
        "output_file_path": "test_cases.xlsx",
        "download_file_name": "test_cases_123.xlsx"
      }
    ],
    "total": 100,
    "page": 1,
    "page_size": 10,
    "total_pages": 10
  }
}
```

#### 4. 删除任务

```http
DELETE /api/v1/task/delete
Content-Type: application/json

{
  "task_id": "123e4567-e89b-12d3-a456-426614174000"
}
```
 > **注意**：删除任务会同时删除 langflow 和本地相关的上传和输出文件

#### 5. 下载文件

```http
GET /api/v1/task/download?task_id=123e4567-e89b-12d3-a456-426614174000
```

#### 6. 静态文件服务

```http
GET /static/*filepath
```

## 使用流程

1. **上传需求文档**：通过 Web 界面或 API 上传 PDF/Word 文档
2. **AI 解析**：Langflow 工作流自动解析文档内容
3. **生成测试用例**：AI 根据需求生成结构化测试用例
4. **下载结果**：下载生成的 Excel 格式测试用例文档

## 开发指南

### 代码架构

项目采用清晰的分层架构：

```
请求 → API 层 → Service 层 → Repo 层 → 数据库
         ↓         ↓           ↓
       参数验证   业务逻辑    数据访问
         ↓         ↓           ↓
       DTO      Assemble     Model
```

### 添加新功能

1. 在 `internal/dto/` 定义请求响应结构
2. 在 `internal/repo/models/` 定义数据模型
3. 在 `internal/repo/` 实现数据访问接口
4. 在 `internal/service/` 实现业务逻辑
5. 在 `internal/assemble/` 添加转换函数
6. 在 `internal/api/` 实现 HTTP 接口
7. 在 `cmd/api/main.go` 注册路由

### 数据库迁移

SQLite 数据库会在首次启动时自动创建，使用 GORM 自动迁移：

```go
db.AutoMigrate(
    &models.Task{},
    // 添加新模型
)
```

### 日志使用

```go
logger.Info("操作成功", zap.String("task_id", taskID))
logger.Error("操作失败", zap.Error(err))
logger.Debug("调试信息", zap.Any("data", obj))
```

### 修改 AI 提示词

如需自定义测试用例生成逻辑，可以修改 `config/prompt.md` 文件：

> **重要提示**：修改提示词时，**必须保持 "3.3 测试用例输出格式" 部分的描述信息不变**，否则会影响用例模板的替换功能，导致生成的测试用例无法正确解析。

**可以修改的部分**：
- 测试用例生成的策略和方法
- 测试场景的覆盖范围
- 测试用例的详细程度
- 其他业务逻辑相关的描述

**不可修改的部分**：
- `3.3 测试用例输出格式` 章节的格式定义
- 输出模板的结构
- 表格列名和格式要求

### 前端开发

```bash
cd frontend

# 开发模式（热重载）
npm run dev

# 代码检查
npm run lint

# 生产构建
npm run build

# 预览构建结果
npm run preview
```

## 常见问题

### Q: Langflow 工作流配置问题？

**A**:
1. **模型名称输入问题**：Langflow 没有自动获取模型列表的接口，需要手动输入模型名称。虽然前端显示可能有问题，但只要输入正确的模型名称，工作流可以正常运行。
2. **组件 ID 获取**：点击工作流中的组件，在右侧设置面板可以看到组件 ID（通常格式为 `ComponentName-xxxxx`）
3. **API Key 权限**：确保 Langflow API Key 有足够的权限执行工作流

### Q: 服务启动失败？

**A**: 检查以下几点：
1. 端口 8080 是否被占用
2. `config/config.yaml` 配置是否正确
3. `data/` 目录是否有写入权限
4. Langflow 服务是否已启动

### Q: Langflow 连接失败？

**A**: 请检查：
1. Langflow 服务是否正常运行（访问 `http://localhost:7860` 验证）
2. `base_url` 配置是否正确（注意不要包含尾部斜杠）
3. `api_key` 是否有效（在 Langflow 设置中验证）
4. `flow_id` 和各个组件 ID 是否正确
5. 网络连接是否正常

### Q: 文件上传失败？

**A**: 可能原因：
1. 文件大小超过限制（默认 50MB）
2. `uploads/` 目录不存在或无写入权限
3. 文件格式不支持
4. Langflow 工作流中的 File 组件配置错误

### Q: AI 生成测试用例失败？

**A**: 检查：
1. OpenAI API 配置是否正确（Base URL、API Key、Model）
2. API Key 是否有足够的额度
3. 模型名称是否正确（区分大小写）
4. 网络是否能访问 LLM API
5. 查看 Langflow 日志了解详细错误信息

### Q: 如何查看日志？

```bash
# 实时查看日志
tail -f logs/flow.log

# 查看最近的错误
grep "ERROR" logs/flow.log
```

### Q: 如何清理数据？

```bash
# 删除数据库文件（会清空所有数据）
rm data/flow_test.db

# 清理上传和输出文件
rm -rf uploads/* outputs/*
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 📧 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 Issue
- 发送邮件至项目维护者

---

**注意**：本项目需要配合 Langflow 服务使用，请确保已正确配置 Langflow 工作流。
