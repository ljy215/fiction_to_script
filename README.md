# AI 小说转剧本工具

AI 小说转剧本工具是一个 Web 应用，目标是帮助小说作者将 3 个章节以上的多语言小说文本改编成一个完整的中文 YAML 剧本初稿。用户可以导入小说、选择剧本类型、通过 AI 智能体生成剧本、在剧本视图编辑器中继续修改，并最终导出 YAML。

具体开发顺序见 [MVP 开发计划](./docs/exec-plans/active/mvp-development-plan.md)。

## 核心能力

- 支持粘贴文本、`.txt`、`.docx`、`.pdf`、`.epub` 导入。
- 输入小说至少需要 3 个章节。
- 支持多语言小说输入。
- 最终输出中文剧本。
- 剧本类型由用户选择，并由不同智能体写作。
- MVP 输出一个完整 YAML 剧本文档。
- 使用剧本视图编辑器编辑内容，并同步 YAML。
- 支持账号登录、云端保存、历史版本和局部重生成。
- MVP 只导出 YAML，不做分镜、图片、视频和非 YAML 导出。

## 技术栈

前端：

- Vite
- React
- JavaScript
- npm

后端：

- Python
- FastAPI
- uv
- `requirements.txt` 作为 pip 复现方式
- SQLite
- SQLAlchemy
- JWT
- LangGraph
- 阿里百炼 API

运行与存储：

- Docker 一键启动
- 本地磁盘文件存储
- FastAPI BackgroundTasks + 数据库任务状态轮询

## 目标目录结构

```text
fiction_to_script/
  AGENTS.md
  README.md
  docker-compose.yml
  docs/
    README.md
    requirements.md
    script-yaml-schema.md
    exec-plans/
      active/
      completed/
  frontend/
    index.html
    package.json
    src/
  backend/
    app/
    Dockerfile
    pyproject.toml
    requirements.txt
  storage/
    data/
    files/
```

## 使用说明

### 1. 配置后端环境变量

后端默认读取 [backend/.env.example](./backend/.env.example)，本地使用前建议复制为 `backend/.env`：

```bash
cd backend
copy .env.example .env
```

必须确认或修改的配置：

- `BAILIAN_API_KEY`：阿里百炼 API Key。真实 AI 生成和局部重生成必须配置真实 Key；不要提交到 Git。
- `BAILIAN_BASE_URL`：阿里百炼兼容模式地址，默认 `https://dashscope.aliyuncs.com/compatible-mode/v1`。
- `BAILIAN_MODEL`：百炼模型名称，例如 `qwen-plus` 或当前可用模型。
- `JWT_SECRET`：登录鉴权密钥，本地可以使用开发值，部署时必须改成强随机字符串。
- `DATABASE_URL`：SQLite 数据库路径，默认 `sqlite:///./storage/data/app.sqlite3`。
- `FILE_STORAGE_DIR`：上传文件保存目录，默认 `./storage/files`。
- `CORS_ORIGINS`：允许访问后端的前端地址，默认包含 `http://localhost:5173` 和 `http://127.0.0.1:5173`。

前端默认请求 `http://127.0.0.1:8000`。如需修改后端地址，可在前端环境变量中设置 `VITE_API_BASE_URL`。

### 2. 启动后端

uv 方式：

```bash
cd backend
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

pip 兜底方式：

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

打开前端：

- http://127.0.0.1:5173

### 4. 基本使用流程

- 注册账号并登录。
- 创建项目，选择剧本类型。
- 粘贴文本或上传 `.txt`、`.docx`、`.pdf`、`.epub` 小说。
- 确认章节识别结果，至少需要 3 章。
- 点击生成中文 YAML 剧本。
- 在剧本视图中编辑行内容，点击“应用”后同步到 YAML。
- 点击“重生成行”或“重生成场景”后，由百炼 AI 局部重写对应内容，并保存为新版本。
- 使用历史版本列表恢复旧版本。
- 校验通过后导出 YAML。

### 5. Docker 一键启动

```bash
docker compose up
```

Docker 服务地址：

- 前端：http://127.0.0.1:5173
- 后端：http://127.0.0.1:8000
- 后端健康检查：http://127.0.0.1:8000/health

本地持久化目录：

- `storage/data`：SQLite 数据文件目录。
- `storage/files`：上传文件和本地文件存储目录。

## 文档入口

- [项目长期记忆与协作规则](./AGENTS.md)
- [文档索引](./docs/README.md)
- [需求文档](./docs/requirements.md)
- [剧本 YAML Schema 说明](./docs/script-yaml-schema.md)
- [MVP 开发计划](./docs/exec-plans/active/mvp-development-plan.md)

## PR 规则

本项目按小 PR 逐步开发：

- 每个 PR 只做一件事。
- 每个 PR 必须保持主分支可运行。
- PR 描述需要包含标题、功能描述、实现思路和测试方式。
- 行为、数据结构、启动方式或目录结构变化时，必须同步更新相关文档。

完整规则见 [AGENTS.md](./AGENTS.md)。
