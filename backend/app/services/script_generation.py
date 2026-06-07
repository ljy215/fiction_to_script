from datetime import datetime, timezone
import json

import yaml
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.agents.nodes import (
    adaptation_planner_node,
    chapter_summarizer_node,
    character_location_extractor_node,
    document_parser_node,
    event_extractor_node,
    language_detector_node,
    schema_validator_node,
    script_writer_node,
    yaml_repair_node,
    yaml_builder_node,
)
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
from app.services.bailian_client import BailianChatMessage, BailianClient, is_mock_bailian_api_key


SCRIPT_TYPE_LABELS = {
    "short_drama": "短剧剧本",
    "film": "影视剧本",
    "audio_drama": "广播剧剧本",
    "stage_play": "舞台剧剧本",
}


def _yaml_scalar(value: object) -> str:
    text = "" if value is None else str(value)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def _mock_script_yaml(project: Project, source: SourceDocument, chapters: list[Chapter], script_type: str | None) -> str:
    now = datetime.now(timezone.utc).isoformat()
    title = project.novel_title or project.name
    script_type_value = script_type or project.script_type or "film"
    script_type_label = SCRIPT_TYPE_LABELS.get(script_type_value, script_type_value)
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
            f"  script_type_label: {_yaml_scalar(script_type_label)}",
            '  fidelity_policy: "faithful"',
            '  output_mode: "single_document"',
            "",
            "generation:",
            '  provider: "mock"',
            '  model: "mock-script-writer"',
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
            '      purpose: "建立主要人物处境并引出核心冲突。"',
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
            '      purpose: "推动主人公作出行动选择。"',
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
    return is_mock_bailian_api_key(settings.bailian_api_key)


def _clean_model_yaml(content: str) -> str:
    text = content.strip()
    if not text.startswith("```"):
        return text

    lines = text.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _build_ai_generation_context(project: Project, source: SourceDocument, state: GenerationGraphState) -> dict[str, object]:
    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "novel_title": project.novel_title,
            "original_author": project.original_author,
            "script_type": state.script_type or project.script_type or "film",
            "script_type_label": SCRIPT_TYPE_LABELS.get(state.script_type or project.script_type or "film", "影视剧本"),
        },
        "source": {
            "id": source.id,
            "source_language": state.source_language,
            "output_language": state.output_language,
        },
        "chapters": state.chapter_summaries,
        "events": state.events,
        "characters": state.characters,
        "locations": state.locations,
        "adaptation": state.adaptation,
        "scene_draft": state.scenes,
    }


def _build_prompt(project: Project, source: SourceDocument, state: GenerationGraphState) -> str:
    context = _build_ai_generation_context(project, source, state)
    return (
        "请基于下面的结构化小说分析结果，真实创作一个完整中文 YAML 剧本初稿。\n"
        "必须严格遵守 docs/script-yaml-schema.md 的顶层结构和字段含义。\n"
        "输出只能是 YAML 正文，不要使用 Markdown 代码块，不要解释。\n"
        "必须包含 schema_version、document、source、script_config、generation、characters、locations、events、adaptation、script.scenes。\n"
        "必须使用提供的稳定 ID，场景 source_refs 必须引用已有 chapter_id 和 event_id。\n"
        "剧本正文必须是中文，并尽量忠实原文章节事件。\n\n"
        f"结构化上下文：\n{json.dumps(context, ensure_ascii=False, indent=2)}"
    )


def _call_bailian(project: Project, source: SourceDocument, state: GenerationGraphState) -> str:
    settings = get_settings()
    prompt = _build_prompt(project, source, state)
    content = BailianClient.from_settings(settings).chat_completion(
        messages=[
            BailianChatMessage(role="system", content="你是专业中文编剧，只输出 YAML。"),
            BailianChatMessage(role="user", content=prompt),
        ],
        temperature=0.4,
    )
    return _clean_model_yaml(content)


def _call_bailian_yaml_repair(
    project: Project,
    source: SourceDocument,
    state: GenerationGraphState,
    invalid_yaml: str,
    validation_errors: list[str],
) -> str:
    context = _build_ai_generation_context(project, source, state)
    prompt = (
        "下面是一份未通过校验的 YAML 剧本。请根据校验错误修复它。\n"
        "只能输出修复后的 YAML 正文，不要解释，不要使用 Markdown 代码块。\n"
        "不得删除必填结构，不得改变已有稳定 ID，所有引用必须存在。\n\n"
        f"校验错误：\n{json.dumps(validation_errors, ensure_ascii=False, indent=2)}\n\n"
        f"结构化上下文：\n{json.dumps(context, ensure_ascii=False, indent=2)}\n\n"
        f"待修复 YAML：\n{invalid_yaml}"
    )
    content = BailianClient.from_settings().chat_completion(
        messages=[
            BailianChatMessage(role="system", content="你是专业 YAML 剧本修复器，只输出修复后的 YAML。"),
            BailianChatMessage(role="user", content=prompt),
        ],
        temperature=0.1,
    )
    return _clean_model_yaml(content)


def _build_complete_yaml(
    project: Project,
    source: SourceDocument,
    state: GenerationGraphState,
    provider: str,
    model: str,
) -> str:
    now = datetime.now(timezone.utc).isoformat()
    title = project.novel_title or project.name
    script_type = state.script_type or project.script_type or "film"
    script_type_label = SCRIPT_TYPE_LABELS.get(script_type, script_type)
    chapters = [
        {
            "id": summary["chapter_id"],
            "order": summary["order"],
            "title": summary["title"],
            "summary": summary["summary"],
        }
        for summary in state.chapter_summaries
    ]
    characters = [
        {
            "id": character["id"],
            "name": character["name"],
            "original_name": character.get("original_name") or "",
            "aliases": character.get("aliases", []),
            "role": character["role"],
            "description": character["description"],
            "motivation": character.get("motivation", "追查事件真相并完成关键选择。"),
            "arc": character.get("arc", "从被动卷入到主动行动。"),
            "source_refs": [{"chapter_id": chapters[0]["id"]}] if chapters else [],
        }
        for character in state.characters
    ]
    locations = [
        {
            "id": location["id"],
            "name": location["name"],
            "original_name": location.get("original_name") or "",
            "type": location["type"],
            "description": location["description"],
            "source_refs": [{"chapter_id": chapters[0]["id"]}] if chapters else [],
        }
        for location in state.locations
    ]
    events = [
        {
            "id": event["id"],
            "chapter_id": event["chapter_id"],
            "order": event["order"],
            "summary": event["summary"],
            "participants": event["participants"],
            "location_id": event["location_id"],
            "consequence": event["consequence"],
            "fidelity_note": "根据原文章节顺序保留核心事件。",
        }
        for event in state.events
    ]
    document_id = f"script_doc_{project.id:03d}"
    payload = {
        "schema_version": "1.0",
        "document": {
            "id": document_id,
            "project_id": f"project_{project.id:03d}",
            "title": f"{title} 改编剧本",
            "status": "draft",
            "created_at": now,
            "updated_at": now,
        },
        "source": {
            "novel_title": project.novel_title or project.name,
            "original_author": project.original_author or "未知",
            "source_language": state.source_language,
            "output_language": state.output_language,
            "minimum_chapters_required": 3,
            "chapter_count": len(chapters),
            "input_files": [],
            "chapters": chapters,
        },
        "script_config": {
            "script_type": script_type,
            "script_type_label": script_type_label,
            "fidelity_policy": "faithful",
            "output_mode": "single_document",
        },
        "generation": {
            "provider": provider,
            "model": model,
            "graph_name": "mvp_script_generation_graph",
            "graph_version": "1.0",
            "generated_at": now,
            "agent_runs": [{"node": node, "status": "success"} for node in state.completed_nodes],
        },
        "characters": characters,
        "locations": locations,
        "events": events,
        "adaptation": state.adaptation,
        "script": {"scenes": state.scenes},
        "editor_state": {
            "current_version_id": "version_001",
            "last_saved_at": now,
        },
        "notes": [
            {
                "id": "note_001",
                "target_id": document_id,
                "level": "suggestion",
                "text": "可以在编辑器中继续细化对白、场景调度和人物弧光。",
            }
        ],
    }
    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, width=120)


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

        task.progress = 60
        task.current_node = "adaptation_planner"
        state = adaptation_planner_node(state, project)
        task.graph_state = state.model_dump_json(ensure_ascii=False)

        task.current_node = "script_writer"
        state = script_writer_node(state)
        task.graph_state = state.model_dump_json(ensure_ascii=False)

        task.progress = 75
        provider = "mock" if _is_mock_configured() else "aliyun_bailian"
        task.provider = provider
        task.model = "mock-script-writer" if provider == "mock" else get_settings().bailian_model
        yaml_content = (
            _build_complete_yaml(project, source, state, provider, task.model)
            if provider == "mock"
            else _call_bailian(project, source, state)
        )
        task.current_node = "yaml_builder"
        state = yaml_builder_node(state, project, yaml_content)
        task.graph_state = state.model_dump_json(ensure_ascii=False)

        task.current_node = "schema_validator"
        state = schema_validator_node(state)
        if state.errors:
            task.current_node = "yaml_repair"
            repaired_yaml = (
                _build_complete_yaml(project, source, state, "mock", "mock-yaml-repair")
                if provider == "mock"
                else _call_bailian_yaml_repair(project, source, state, yaml_content, state.errors)
            )
            state = yaml_repair_node(state, repaired_yaml)
            task.graph_state = state.model_dump_json(ensure_ascii=False)

            task.current_node = "schema_validator"
            state = schema_validator_node(state)
            if state.errors:
                raise ValueError("; ".join(state.errors))
            yaml_content = state.yaml_content or repaired_yaml
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
