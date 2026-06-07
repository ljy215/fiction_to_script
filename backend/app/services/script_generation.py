from datetime import datetime, timezone
import json

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.agents.nodes import (
    chapter_summarizer_node,
    character_location_extractor_node,
    document_parser_node,
    event_extractor_node,
    language_detector_node,
    schema_validator_node,
    yaml_builder_node,
)
from app.agents.script_profiles import get_agent_profile
from app.agents.state import GenerationGraphState
from app.config import get_settings
from app.models import (
    Chapter,
    ChapterSummary,
    GenerationTask,
    Project,
    ScriptDocument,
    SourceDocument,
    StoryCharacter,
    StoryEvent,
    StoryLocation,
)


def _yaml_scalar(value: object) -> str:
    text = "" if value is None else str(value)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def _mock_script_yaml(project: Project, source: SourceDocument, chapters: list[Chapter], script_type: str | None) -> str:
    now = datetime.now(timezone.utc).isoformat()
    title = project.novel_title or project.name
    profile = get_agent_profile(script_type or project.script_type)
    script_type_value = profile.script_type.value
    first_chapter = chapters[0] if chapters else None
    second_chapter = chapters[1] if len(chapters) > 1 else first_chapter
    third_chapter = chapters[2] if len(chapters) > 2 else second_chapter

    chapter_lines = []
    for chapter in chapters:
        summary = chapter.content_text[:80].replace("\n", " ")
        chapter_lines.extend(
            [
                f"    - id: {_yaml_scalar(f'ch_{chapter.order:03d}')}",
                f"      order: {chapter.order}",
                f"      title: {_yaml_scalar(chapter.title)}",
                f"      summary: {_yaml_scalar(summary)}",
            ]
        )

    return "\n".join(
        [
            'schema_version: "1.0"',
            "",
            "document:",
            f"  id: {_yaml_scalar(f'script_doc_{project.id:03d}')}",
            f"  project_id: {_yaml_scalar(f'project_{project.id:03d}')}",
            f"  title: {_yaml_scalar(f'{title} 改编剧本')}",
            '  status: "draft"',
            f"  created_at: {_yaml_scalar(now)}",
            f"  updated_at: {_yaml_scalar(now)}",
            "",
            "source:",
            f"  novel_title: {_yaml_scalar(project.novel_title or project.name)}",
            f"  original_author: {_yaml_scalar(project.original_author or '未知')}",
            '  source_language: "auto"',
            '  output_language: "zh-CN"',
            "  minimum_chapters_required: 3",
            f"  chapter_count: {len(chapters)}",
            "  input_files: []",
            "  chapters:",
            *chapter_lines,
            "",
            "script_config:",
            f"  script_type: {_yaml_scalar(script_type_value)}",
            f"  script_type_label: {_yaml_scalar(profile.label)}",
            '  fidelity_policy: "faithful"',
            '  output_mode: "single_document"',
            f"  agent_profile: {_yaml_scalar(profile.graph_name)}",
            f"  writing_strategy: {_yaml_scalar(profile.strategy)}",
            "",
            "generation:",
            '  provider: "mock"',
            '  model: "mock-script-writer"',
            f"  graph_name: {_yaml_scalar(profile.graph_name)}",
            f"  graph_version: {_yaml_scalar(profile.graph_version)}",
            f"  generated_at: {_yaml_scalar(now)}",
            "  agent_runs:",
            '    - node: "chapter_reader"',
            '      status: "success"',
            '    - node: "yaml_builder"',
            '      status: "success"',
            "",
            "characters:",
            '  - id: "char_001"',
            '    name: "主人公"',
            '    original_name: ""',
            '    aliases: []',
            '    role: "protagonist"',
            f"    description: {_yaml_scalar('根据导入小说自动生成的核心人物占位，可在编辑器中继续细化。')}",
            '    motivation: "追查事件真相并完成关键选择。"',
            '    arc: "从被动卷入到主动行动。"',
            "    source_refs:",
            f"      - chapter_id: {_yaml_scalar(f'ch_{first_chapter.order:03d}' if first_chapter else 'ch_001')}",
            "",
            "locations:",
            '  - id: "loc_001"',
            '    name: "主要场景"',
            '    original_name: ""',
            '    type: "mixed"',
            '    description: "由小说前三章核心事件归纳出的主要行动空间。"',
            "    source_refs:",
            f"      - chapter_id: {_yaml_scalar(f'ch_{first_chapter.order:03d}' if first_chapter else 'ch_001')}",
            "",
            "events:",
            '  - id: "evt_001"',
            f"    chapter_id: {_yaml_scalar(f'ch_{first_chapter.order:03d}' if first_chapter else 'ch_001')}",
            "    order: 1",
            f"    summary: {_yaml_scalar((first_chapter.content_text[:100] if first_chapter else '主人公进入故事核心情境。'))}",
            '    participants: ["char_001"]',
            '    location_id: "loc_001"',
            '    consequence: "主人公开始面对主要冲突。"',
            '    fidelity_note: "基于导入章节内容生成，后续可由真实模型进一步细化。"',
            "",
            "adaptation:",
            f"  logline: {_yaml_scalar(f'{title} 的主人公在连续事件中发现冲突真相，并做出关键选择。')}",
            '  theme: "选择、真相与成长"',
            "  strategy:",
            '    preserved_events: ["evt_001"]',
            "    merged_events: []",
            "    omitted_events: []",
            "    added_bridges:",
            '      - "为连接章节事件补充少量过渡动作。"',
            "  notes:",
            '    - "mock 模式用于无 API Key 时演示完整小说转剧本流程。"',
            "",
            "script:",
            "  scenes:",
            '    - id: "sc_001"',
            "      order: 1",
            '      heading: "内景 主要场景 夜"',
            '      location_id: "loc_001"',
            '      interior_exterior: "interior"',
            '      time_of_day: "night"',
            f"      purpose: {_yaml_scalar(profile.scene_focus)}",
            '      conflict: "主人公必须判断眼前线索是否可信。"',
            '      outcome: "主人公决定继续追查。"',
            "      source_refs:",
            f"        - chapter_id: {_yaml_scalar(f'ch_{second_chapter.order:03d}' if second_chapter else 'ch_001')}",
            '          event_id: "evt_001"',
            "      lines:",
            '        - id: "line_001"',
            '          type: "action"',
            '          text: "夜色压下来，主人公停在门口，听见屋内传来细微声响。"',
            '        - id: "line_002"',
            '          type: "dialogue"',
            '          character_id: "char_001"',
            '          speaker: "主人公"',
            '          text: "这件事不会无缘无故发生。"',
            '          emotion: "警觉"',
            '    - id: "sc_002"',
            "      order: 2",
            '      heading: "外景 转折地点 清晨"',
            '      location_id: "loc_001"',
            '      interior_exterior: "exterior"',
            '      time_of_day: "morning"',
            f"      purpose: {_yaml_scalar(profile.line_focus)}",
            '      conflict: "新的线索与过去认知发生冲突。"',
            '      outcome: "主人公踏上下一阶段调查。"',
            "      source_refs:",
            f"        - chapter_id: {_yaml_scalar(f'ch_{third_chapter.order:03d}' if third_chapter else 'ch_001')}",
            '          event_id: "evt_001"',
            "      lines:",
            '        - id: "line_003"',
            '          type: "action"',
            '          text: "晨光照亮空旷的路，主人公攥紧线索，转身离开。"',
            '        - id: "line_004"',
            '          type: "transition"',
            '          text: "切至："',
            "",
            "editor_state:",
            '  current_version_id: "version_001"',
            f"  last_saved_at: {_yaml_scalar(now)}",
            "",
            "notes:",
            '  - id: "note_001"',
            '    target_id: "script_doc_001"',
            '    level: "suggestion"',
            '    text: "可在编辑器中继续替换 mock 内容，或配置真实百炼 API 后重新生成。"',
        ]
    )


def _is_mock_configured() -> bool:
    settings = get_settings()
    api_key = settings.bailian_api_key.strip().lower()
    return api_key in {"", "mock", "dev-placeholder-bailian-api-key"}


def _build_prompt(project: Project, chapters: list[Chapter], script_type: str | None) -> str:
    profile = get_agent_profile(script_type or project.script_type)
    chapter_context = "\n\n".join(
        f"{chapter.title}\n{chapter.content_text[:2000]}" for chapter in chapters[:8]
    )
    return (
        "请把下面小说章节改编成一个完整中文 YAML 剧本。"
        "必须遵守项目 docs/script-yaml-schema.md 的顶层结构，输出只能是 YAML，不要解释。\n"
        f"剧本类型：{profile.label}\n"
        f"写作策略：{profile.strategy}\n"
        f"场景侧重：{profile.scene_focus}\n"
        f"台词侧重：{profile.line_focus}\n"
        f"小说名：{project.novel_title or project.name}\n"
        f"原作者：{project.original_author or '未知'}\n\n"
        f"小说章节：\n{chapter_context}"
    )


def _call_bailian(project: Project, chapters: list[Chapter], script_type: str | None) -> str:
    settings = get_settings()
    prompt = _build_prompt(project, chapters, script_type)
    response = httpx.post(
        f"{settings.bailian_base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {settings.bailian_api_key}"},
        json={
            "model": settings.bailian_model,
            "messages": [
                {"role": "system", "content": "你是专业中文编剧，只输出 YAML。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.4,
        },
        timeout=90,
    )
    response.raise_for_status()
    payload = response.json()
    return payload["choices"][0]["message"]["content"].strip()


def _persist_story_intermediates(
    db: Session,
    task: GenerationTask,
    state: GenerationGraphState,
    provider: str,
    model: str,
) -> None:
    db.execute(
        delete(ChapterSummary).where(
            ChapterSummary.project_id == task.project_id,
            ChapterSummary.source_document_id == task.source_document_id,
            ChapterSummary.owner_id == task.owner_id,
        )
    )
    db.execute(
        delete(StoryEvent).where(
            StoryEvent.project_id == task.project_id,
            StoryEvent.source_document_id == task.source_document_id,
            StoryEvent.owner_id == task.owner_id,
        )
    )
    db.execute(
        delete(StoryCharacter).where(
            StoryCharacter.project_id == task.project_id,
            StoryCharacter.source_document_id == task.source_document_id,
            StoryCharacter.owner_id == task.owner_id,
        )
    )
    db.execute(
        delete(StoryLocation).where(
            StoryLocation.project_id == task.project_id,
            StoryLocation.source_document_id == task.source_document_id,
            StoryLocation.owner_id == task.owner_id,
        )
    )

    for summary in state.chapter_summaries:
        db.add(
            ChapterSummary(
                owner_id=task.owner_id,
                project_id=task.project_id,
                source_document_id=task.source_document_id,
                chapter_id=summary["database_id"],
                chapter_order=summary["order"],
                chapter_title=summary["title"],
                summary=summary["summary"],
                provider=provider,
                model=model,
            )
        )

    for character in state.characters:
        db.add(
            StoryCharacter(
                owner_id=task.owner_id,
                project_id=task.project_id,
                source_document_id=task.source_document_id,
                character_key=character["id"],
                name=character["name"],
                original_name=character.get("original_name"),
                role=character["role"],
                description=character["description"],
                provider=provider,
                model=model,
            )
        )

    for location in state.locations:
        db.add(
            StoryLocation(
                owner_id=task.owner_id,
                project_id=task.project_id,
                source_document_id=task.source_document_id,
                location_key=location["id"],
                name=location["name"],
                original_name=location.get("original_name"),
                location_type=location["type"],
                description=location["description"],
                provider=provider,
                model=model,
            )
        )

    for event in state.events:
        db.add(
            StoryEvent(
                owner_id=task.owner_id,
                project_id=task.project_id,
                source_document_id=task.source_document_id,
                chapter_id=event["chapter_database_id"],
                event_key=event["id"],
                event_order=event["order"],
                summary=event["summary"],
                participants_json=json.dumps(event["participants"], ensure_ascii=False),
                location_name=event.get("location_name"),
                consequence=event["consequence"],
                provider=provider,
                model=model,
            )
        )


def run_generation_task(db: Session, task_id: int) -> None:
    task = db.get(GenerationTask, task_id)
    if task is None:
        return

    try:
        task.status = "running"
        task.progress = 20
        project = db.get(Project, task.project_id)
        source = db.get(SourceDocument, task.source_document_id)
        if project is None or source is None:
            raise ValueError("Project or source document not found")

        chapters = db.execute(
            select(Chapter)
            .where(
                Chapter.source_document_id == source.id,
                Chapter.project_id == project.id,
                Chapter.owner_id == task.owner_id,
            )
            .order_by(Chapter.order)
        ).scalars().all()
        if len(chapters) < 3:
            raise ValueError("At least 3 chapters are required before generation")

        state = GenerationGraphState(
            project_id=project.id,
            source_document_id=source.id,
            script_type=project.script_type,
        )
        task.current_node = "document_parser"
        state = document_parser_node(state, source, chapters)
        task.graph_state = state.model_dump_json(ensure_ascii=False)

        task.current_node = "language_detector"
        state = language_detector_node(state, source)
        task.graph_state = state.model_dump_json(ensure_ascii=False)

        task.progress = 40
        task.current_node = "chapter_summarizer"
        state = chapter_summarizer_node(state)
        task.graph_state = state.model_dump_json(ensure_ascii=False)

        task.current_node = "event_extractor"
        state = event_extractor_node(state)
        task.graph_state = state.model_dump_json(ensure_ascii=False)

        task.current_node = "character_location_extractor"
        state = character_location_extractor_node(state)
        task.graph_state = state.model_dump_json(ensure_ascii=False)
        _persist_story_intermediates(db, task, state, "mock", "mock-story-analyzer")

        task.progress = 70
        provider = "mock" if _is_mock_configured() else "aliyun_bailian"
        task.provider = provider
        task.model = "mock-script-writer" if provider == "mock" else get_settings().bailian_model
        yaml_content = (
            _mock_script_yaml(project, source, chapters, project.script_type)
            if provider == "mock"
            else _call_bailian(project, chapters, project.script_type)
        )
        task.current_node = "yaml_builder"
        state = yaml_builder_node(state, project, yaml_content)
        task.graph_state = state.model_dump_json(ensure_ascii=False)

        task.current_node = "schema_validator"
        state = schema_validator_node(state)
        if state.errors:
            raise ValueError("; ".join(state.errors))
        task.graph_state = state.model_dump_json(ensure_ascii=False)

        script = ScriptDocument(
            owner_id=task.owner_id,
            project_id=task.project_id,
            source_document_id=task.source_document_id,
            title=f"{project.novel_title or project.name} 改编剧本",
            script_type=project.script_type,
            yaml_content=yaml_content,
            version_number=1,
        )
        db.add(script)
        db.flush()

        task.script_document_id = script.id
        task.status = "succeeded"
        task.current_node = "done"
        task.progress = 100
        task.finished_at = datetime.now(timezone.utc)
        project.status = "ready"
        db.commit()
    except Exception as exc:
        task.status = "failed"
        task.current_node = "failed"
        task.error_message = str(exc)
        task.progress = 100
        task.finished_at = datetime.now(timezone.utc)
        project = db.get(Project, task.project_id)
        if project is not None:
            project.status = "failed"
        db.commit()
