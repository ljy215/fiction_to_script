# AI 小说转剧本工具

AI 小说转剧本工具是一个 Web 应用，目标是帮助小说作者将 3 个章节以上的多语言小说文本改编成一个完整的中文 YAML 剧本初稿。用户可以导入小说、选择剧本类型、通过 AI 智能体生成剧本、在剧本视图编辑器中继续修改，并最终导出 YAML。

当前仓库处于 MVP 项目骨架阶段，已创建前端 Vite React JavaScript 脚手架和后端 FastAPI 脚手架。具体开发顺序见 [MVP 开发计划](./docs/exec-plans/active/mvp-development-plan.md)。

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
    pyproject.toml
    requirements.txt
  storage/
```

当前已完成 PR-001 文档入口、PR-002 前端脚手架和 PR-003 后端 FastAPI 脚手架。`docker-compose.yml` 和完整 Docker 启动脚本会在后续 PR 中逐步添加。

## 本地启动入口

当前可以启动前端开发服务器：

```bash
# 前端
cd frontend
npm install
npm run dev
```

当前可以启动后端开发服务器：

```bash
# 后端，uv 方式
cd backend
uv sync
uv run fastapi dev app/main.py
```

```bash
# 后端，pip 兜底方式
cd backend
python -m venv .venv
pip install -r requirements.txt
fastapi dev app/main.py
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

Docker 启动入口会在后续 PR 中补充：

```bash
# Docker 一键启动
docker compose up
```

实际命令以后续脚手架 PR 中提交的脚本为准，根目录 README 会同步更新。

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
