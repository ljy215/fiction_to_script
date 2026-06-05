# AGENTS.md

This file is the short, durable entry point for future agents working in this repository.

Keep this file concise. Put detailed requirements, schemas, architecture notes, and execution plans under `docs/`, then link to them here. When implementation decisions change, update the relevant source document in the same PR.

## Project Memory

- Product: AI-assisted novel-to-script Web application.
- Frontend: Vite + React + JavaScript.
- Frontend package manager: npm.
- Backend: Python + FastAPI.
- Backend dependency management: uv is primary; also maintain `requirements.txt` for pip-based reproduction.
- Database: SQLite for the MVP.
- ORM: SQLAlchemy.
- Authentication: JWT.
- Agent orchestration: LangGraph.
- Initial model provider: Alibaba Bailian API.
- File storage: local disk for the MVP.
- Long-running jobs: FastAPI BackgroundTasks plus database task-status polling.
- Deployment/dev startup: Docker one-command startup is required.
- Input: pasted text, `.txt`, `.docx`, `.pdf`, `.epub`.
- Minimum source content: at least 3 chapters.
- Source language: multilingual.
- Output language: Chinese script.
- Script output: one complete YAML document in the MVP.
- Editing model: screenplay view editor synchronized with YAML.
- Required platform features: account login, cloud save, history versions, partial regeneration.
- Not in MVP: multi-user collaboration, image generation, storyboard generation, video generation, non-YAML export.

## Source Documents

- Product requirements: `docs/requirements.md`
- YAML schema design: `docs/script-yaml-schema.md`
- Active MVP development plan: `docs/exec-plans/active/mvp-development-plan.md`
- Documentation index: `docs/README.md`

## Working Rules

- Read `docs/requirements.md`, `docs/script-yaml-schema.md`, and the active execution plan before starting feature work.
- Keep each change scoped to one PR-sized feature.
- Update docs in the same PR when behavior, data shape, workflow, dependencies, or project structure changes.
- Keep the main branch runnable after every merge.
- Prefer small, verifiable increments over large mixed changes.
- Keep `AGENTS.md` as a map and durable memory file, not a full design document.

## PR Submission Rules

All work in this repository must follow these Pull Request rules.

- New features must be added through PRs.
- Each PR must do only one thing.
- Each PR should implement or modify a single feature.
- PRs should be as small and fine-grained as practical.
- Large features must be split into multiple independent PRs and submitted step by step.

Every PR title and description must be clear and complete.

Required PR content:

- Title: one sentence explaining what this PR adds or changes.
- Feature description: explain what the feature does and how to use it.
- Implementation approach: briefly explain the technical choices or core implementation logic.
- Test method: explain how to verify that the feature works correctly.

After a PR is merged, the main branch must remain runnable. Reviewers or judges should be able to reproduce the demo effect from the main branch at any time.

If working as a team, each team only needs to submit one repository URL. Team members must use their own accounts to submit commits, and PR descriptions must clearly describe each member's contribution.

If the project contains multiple independent modules, manage them in different subdirectories in the same repository:

- `/frontend` for the Vite React JavaScript app.
- `/backend` for the FastAPI API and LangGraph orchestration.

## Documentation Maintenance

This repository follows a docs-as-operating-context style inspired by OpenAI's harness engineering article: keep persistent context in repository files, keep entry points short, and make plans executable and reviewable.

Maintenance rules:

- Add or update an execution plan before starting a multi-step feature.
- Store active plans in `docs/exec-plans/active/`.
- Move completed plans to `docs/exec-plans/completed/` when the work is done.
- Record product decisions in `docs/requirements.md`.
- Record YAML structure decisions in `docs/script-yaml-schema.md`.
- Record architecture decisions in dedicated docs when they outgrow this file.
- Do not duplicate long explanations in `AGENTS.md`; link to the relevant doc instead.
