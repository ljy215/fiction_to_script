# Project Documentation Index

This directory is the project source of truth for product, schema, and development planning.

## Core Documents

- [Root README](../README.md)
- [Project memory and working rules](../AGENTS.md)
- [Product requirements](./requirements.md)
- [Script YAML schema](./script-yaml-schema.md)
- [Active MVP development plan](./exec-plans/active/mvp-development-plan.md)

## How To Maintain Docs

- Keep `AGENTS.md` short and use it as a navigation file.
- Put detailed product decisions in `requirements.md`.
- Put data structure and validation decisions in `script-yaml-schema.md`.
- Put implementation sequencing in `exec-plans/`.
- Update the affected document in the same PR as the related code change.
- Keep active plans under `exec-plans/active/`.
- Move completed plans under `exec-plans/completed/`.

## Current Product Direction

The MVP is a Web application that converts at least 3 chapters of multilingual novel text into one complete Chinese YAML script. The frontend uses Vite + React + JavaScript with npm. The backend uses Python + FastAPI, uv as the primary dependency manager, `requirements.txt` as the pip fallback, SQLite, SQLAlchemy, JWT authentication, LangGraph orchestration, Alibaba Bailian API as the first model provider, local disk file storage, BackgroundTasks plus database polling for long-running jobs, and Docker for one-command startup.
