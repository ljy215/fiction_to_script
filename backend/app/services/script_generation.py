from datetime import datetime, timezone
import json

import yaml
from sqlalchemy import delete, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

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

CHAPTER_CONTEXT_CHAR_LIMIT = 12000
CHAPTER_DIALOGUE_SAMPLE_LIMIT = 12


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


def _dialogue_samples(text: str) -> list[str]:
    samples: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "“" in line or "”" in line or line.startswith(("\"", "'")):
            samples.append(line[:300])
        if len(samples) >= CHAPTER_DIALOGUE_SAMPLE_LIMIT:
            break
    return samples


def _chapter_source_blocks(state: GenerationGraphState) -> list[dict[str, object]]:
    blocks = []
    for chapter in state.chapters:
        content = str(chapter.get("content") or "")
        truncated = len(content) > CHAPTER_CONTEXT_CHAR_LIMIT
        blocks.append(
            {
                "chapter_id": chapter["id"],
                "order": chapter["order"],
                "title": chapter["title"],
                "content_length": chapter["content_length"],
                "content": content[:CHAPTER_CONTEXT_CHAR_LIMIT],
                "is_truncated": truncated,
                "dialogue_samples": _dialogue_samples(content),
                "event_id": f"evt_{int(chapter['order']):03d}",
            }
        )
    return blocks


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
            "chapter_count": len(state.chapters),
        },
        "source_chapters": _chapter_source_blocks(state),
        "chapter_summaries": state.chapter_summaries,
        "events": state.events,
        "characters": state.characters,
        "locations": state.locations,
        "adaptation": state.adaptation,
    }


def _build_prompt(project: Project, source: SourceDocument, state: GenerationGraphState) -> str:
    context = _build_ai_generation_context(project, source, state)
    return (
        "你要把小说原文按章节直接改编成完整中文 YAML 剧本初稿。\n"
        "下面的 source_chapters 已经按章节切分，每一项都包含 chapter_id、event_id、title、原文 content 和对白样例。\n"
        "请优先依据 source_chapters.content 改编，不要只依据摘要，不要把章节压缩成泛泛的几句话。\n\n"
        "硬性输出要求：\n"
        "1. 只能输出 YAML 正文，不要 Markdown 代码块，不要解释。\n"
        "2. 必须严格使用 docs/script-yaml-schema.md 的顶层结构：schema_version、document、source、script_config、generation、characters、locations、events、adaptation、script.scenes、editor_state、notes。\n"
        "3. source.chapters 要列出所有输入章节；events 至少每章 1 个，并使用提供的 event_id。\n"
        "4. script.scenes 必须按章节顺序展开：每章至少 1 场；动作/冲突强的章节生成 2-4 场。\n"
        "5. 不要合并成“主要场景”这类空泛场景；heading 要根据原文地点、时间、内外景具体命名。\n"
        "6. 必须保留并改写原文中的关键对白。对白密集章节，每章至少写 4-10 行 dialogue；战斗/行动章节要写足 action 细节。\n"
        "7. 每个 scene.source_refs 必须引用对应 chapter_id 和 event_id，所有 character_id、location_id 引用必须存在。\n"
        "8. 改编策略是尽量忠实原文，允许少量过场衔接，但不得大幅删减关键对话、战斗动作、人物选择和场景推进。\n"
        "9. 每场 scenes.lines 不能只有人物对话和地点。每场至少 8 行 lines，其中至少 3 行 action 用来写背景环境、天气、光线、声音、道具、人物走位、表情和肢体动作。\n"
        "10. 每场开头必须先写 1-3 行 action 建立画面背景，再进入对白；对白之间也要穿插动作和环境变化。\n"
        "11. 战斗、埋伏、追逐、修炼类章节要以 action 为主，写清空间关系、攻防动作、伤势、节奏变化和现场氛围，不能概括成一句话。\n"
        "12. characters 和 locations 要尽量从原文抽取真实姓名和地点名，不要使用“主人公”“主要场景”这类占位名，除非原文没有提供。\n"
        "13. 输出语言必须是中文，YAML 字符串请正确转义。\n\n"
        f"章节级原文上下文：\n{json.dumps(context, ensure_ascii=False, indent=2)}"
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


def _call_bailian_streaming(
    project: Project,
    source: SourceDocument,
    state: GenerationGraphState,
    on_partial_yaml,
) -> str:
    settings = get_settings()
    prompt = _build_prompt(project, source, state)
    chunks: list[str] = []
    for chunk in BailianClient.from_settings(settings).chat_completion_stream(
        messages=[
            BailianChatMessage(role="system", content="你是专业中文编剧，只输出 YAML。"),
            BailianChatMessage(role="user", content=prompt),
        ],
        temperature=0.4,
    ):
        chunks.append(chunk)
        on_partial_yaml("".join(chunks))
    return _clean_model_yaml("".join(chunks))


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


def _normalize_ai_yaml_content(
    project: Project,
    state: GenerationGraphState,
    yaml_content: str,
    provider: str,
    model: str,
) -> str:
    try:
        payload = yaml.safe_load(yaml_content)
    except yaml.YAMLError:
        return yaml_content

    if not isinstance(payload, dict):
        return yaml_content

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
    chapter_ids = {chapter["id"] for chapter in chapters}

    document = payload.setdefault("document", {})
    if isinstance(document, dict):
        document.setdefault("id", f"script_doc_{project.id:03d}")
        document.setdefault("project_id", f"project_{project.id:03d}")
        document.setdefault("title", f"{title} 改编剧本")
        document.setdefault("status", "draft")
        document.setdefault("created_at", now)
        document.setdefault("updated_at", now)

    source_payload = payload.setdefault("source", {})
    if isinstance(source_payload, dict):
        source_payload["novel_title"] = source_payload.get("novel_title") or title
        source_payload["original_author"] = source_payload.get("original_author") or project.original_author or "未知"
        source_payload["source_language"] = source_payload.get("source_language") or state.source_language
        source_payload["output_language"] = "zh-CN"
        source_payload["minimum_chapters_required"] = 3
        source_payload["chapter_count"] = len(chapters)
        source_payload.setdefault("input_files", [])
        source_payload["chapters"] = chapters

    script_config = payload.setdefault("script_config", {})
    if isinstance(script_config, dict):
        script_config["script_type"] = script_type
        script_config["script_type_label"] = script_type_label
        script_config["fidelity_policy"] = script_config.get("fidelity_policy") or "faithful"
        script_config["output_mode"] = script_config.get("output_mode") or "single_document"

    generation = payload.setdefault("generation", {})
    if isinstance(generation, dict):
        generation["provider"] = provider
        generation["model"] = model
        generation.setdefault("graph_name", "mvp_script_generation_graph")
        generation.setdefault("graph_version", "1.0")
        generation["generated_at"] = generation.get("generated_at") or now
        generation.setdefault("agent_runs", [{"node": node, "status": "success"} for node in state.completed_nodes])

    characters = payload.get("characters")
    if not isinstance(characters, list) or not characters:
        characters = state.characters
        payload["characters"] = characters
    for index, character in enumerate(characters):
        if not isinstance(character, dict):
            continue
        character.setdefault("id", f"char_{index + 1:03d}")
        character.setdefault("name", character["id"])
        character.setdefault("role", "supporting")
        character.setdefault("original_name", "")
        character.setdefault("aliases", [])
        character.setdefault("description", "")
        character.setdefault("motivation", "")
        character.setdefault("arc", "")
        character.setdefault("source_refs", [{"chapter_id": chapters[0]["id"]}] if chapters else [])
    character_ids = {character["id"] for character in characters if isinstance(character, dict) and character.get("id")}
    first_character_id = next(iter(character_ids), "char_001")

    locations = payload.get("locations")
    if not isinstance(locations, list) or not locations:
        locations = state.locations
        payload["locations"] = locations
    for index, location in enumerate(locations):
        if not isinstance(location, dict):
            continue
        location.setdefault("id", f"loc_{index + 1:03d}")
        location.setdefault("name", location["id"])
        location.setdefault("original_name", "")
        location.setdefault("type", "mixed")
        location.setdefault("description", "")
        location.setdefault("source_refs", [{"chapter_id": chapters[0]["id"]}] if chapters else [])
    location_ids = {location["id"] for location in locations if isinstance(location, dict) and location.get("id")}
    first_location_id = next(iter(location_ids), "loc_001")

    events = payload.get("events")
    if not isinstance(events, list) or not events:
        events = state.events
        payload["events"] = events
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            continue
        fallback_chapter = chapters[min(index, len(chapters) - 1)]["id"] if chapters else "ch_001"
        event.setdefault("id", f"evt_{index + 1:03d}")
        if event.get("chapter_id") not in chapter_ids:
            event["chapter_id"] = fallback_chapter
        event.setdefault("order", index + 1)
        event["summary"] = event.get("summary") or event.get("title") or event.get("description") or "原文章节事件。"
        participants = event.get("participants")
        if not isinstance(participants, list) or not participants:
            event["participants"] = [first_character_id]
        else:
            event["participants"] = [participant for participant in participants if participant in character_ids] or [first_character_id]
        if event.get("location_id") not in location_ids:
            event["location_id"] = first_location_id
        event.setdefault("consequence", event["summary"])
        event.setdefault("fidelity_note", "根据原文章节内容改编。")
    event_ids = {event["id"] for event in events if isinstance(event, dict) and event.get("id")}

    adaptation = payload.setdefault("adaptation", {})
    if isinstance(adaptation, dict):
        adaptation.setdefault("logline", f"{title} 的中文剧本改编。")
        adaptation.setdefault("theme", "成长、选择与冲突")
        strategy = adaptation.setdefault("strategy", {})
        if isinstance(strategy, dict):
            strategy.setdefault("preserved_events", [event["id"] for event in events if isinstance(event, dict) and event.get("id")])
            strategy.setdefault("merged_events", [])
            strategy.setdefault("omitted_events", [])
            strategy.setdefault("added_bridges", [])
        adaptation.setdefault("notes", [])

    script = payload.setdefault("script", {})
    scenes = script.get("scenes") if isinstance(script, dict) else None
    if not isinstance(scenes, list):
        scenes = []
        script["scenes"] = scenes
    for scene_index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            continue
        fallback_event = events[min(scene_index, len(events) - 1)] if events else {}
        fallback_chapter_id = fallback_event.get("chapter_id") or (chapters[0]["id"] if chapters else "ch_001")
        fallback_event_id = fallback_event.get("id") or "evt_001"
        scene.setdefault("id", scene.get("scene_id") or f"sc_{scene_index + 1:03d}")
        scene.setdefault("order", scene_index + 1)
        scene.setdefault("heading", scene.get("title") or f"场景 {scene_index + 1}")
        if scene.get("location_id") not in location_ids:
            scene["location_id"] = fallback_event.get("location_id") if fallback_event.get("location_id") in location_ids else first_location_id
        scene.setdefault("interior_exterior", "interior")
        scene.setdefault("time_of_day", "day")
        scene.setdefault("purpose", scene.get("summary") or "呈现原文章节事件。")
        scene.setdefault("conflict", fallback_event.get("summary") or "人物面对新的冲突。")
        scene.setdefault("outcome", fallback_event.get("consequence") or "事件继续推进。")
        source_refs = scene.get("source_refs")
        if not isinstance(source_refs, list) or not source_refs:
            scene["source_refs"] = [{"chapter_id": fallback_chapter_id, "event_id": fallback_event_id}]
        else:
            for ref in source_refs:
                if not isinstance(ref, dict):
                    continue
                if ref.get("chapter_id") not in chapter_ids:
                    ref["chapter_id"] = fallback_chapter_id
                if ref.get("event_id") not in event_ids:
                    ref["event_id"] = fallback_event_id

        lines = scene.get("lines")
        if not isinstance(lines, list):
            lines = []
            scene["lines"] = lines
        for line_index, line in enumerate(lines):
            if not isinstance(line, dict):
                continue
            line.setdefault("id", f"line_{scene_index + 1:03d}_{line_index + 1:03d}")
            line["text"] = line.get("text") or line.get("content") or line.get("description") or ""
            line_type = line.get("type") or "action"
            if line_type not in {"action", "dialogue", "narration", "sound", "transition", "stage_direction", "note"}:
                line_type = "action"
            line["type"] = line_type
            if line_type == "dialogue" and line.get("character_id") not in character_ids:
                line["character_id"] = first_character_id

    editor_state = payload.setdefault("editor_state", {})
    if isinstance(editor_state, dict):
        editor_state.setdefault("current_version_id", "version_001")
        editor_state.setdefault("last_saved_at", now)

    payload.setdefault("notes", [])
    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, width=120)


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


def _save_task_progress(db: Session, task: GenerationTask, state: GenerationGraphState | None = None) -> None:
    if state is not None:
        task.graph_state = state.model_dump_json(ensure_ascii=False)
    task.updated_at = datetime.now(timezone.utc)
    db.add(task)
    db.commit()


def run_generation_task(db: Session, task_id: int) -> None:
    task = db.get(GenerationTask, task_id)
    if task is None:
        return

    try:
        task.status = "running"
        task.progress = 20
        _save_task_progress(db, task)
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
        _save_task_progress(db, task, state)

        task.current_node = "language_detector"
        state = language_detector_node(state, source)
        _save_task_progress(db, task, state)

        task.progress = 40
        task.current_node = "chapter_summarizer"
        state = chapter_summarizer_node(state)
        _save_task_progress(db, task, state)

        task.current_node = "event_extractor"
        state = event_extractor_node(state)
        _save_task_progress(db, task, state)

        task.current_node = "character_location_extractor"
        state = character_location_extractor_node(state)
        _save_task_progress(db, task, state)
        _persist_story_intermediates(db, task, state, "mock", "mock-story-analyzer")
        db.commit()

        task.progress = 60
        task.current_node = "adaptation_planner"
        state = adaptation_planner_node(state, project)
        _save_task_progress(db, task, state)

        task.current_node = "script_writer"
        state = script_writer_node(state)
        _save_task_progress(db, task, state)

        task.progress = 75
        provider = "mock" if _is_mock_configured() else "aliyun_bailian"
        task.provider = provider
        task.model = "mock-script-writer" if provider == "mock" else get_settings().bailian_model
        _save_task_progress(db, task, state)
        task.current_node = "yaml_builder"
        task.progress = 80
        _save_task_progress(db, task, state)

        if provider == "mock":
            yaml_content = _build_complete_yaml(project, source, state, provider, task.model)
        else:
            last_saved_length = 0

            def save_partial_yaml(partial_yaml: str) -> None:
                nonlocal last_saved_length
                if len(partial_yaml) - last_saved_length < 300:
                    return
                state.yaml_content = partial_yaml
                task.progress = min(95, 80 + len(partial_yaml) // 1200)
                _save_task_progress(db, task, state)
                last_saved_length = len(partial_yaml)

            yaml_content = _call_bailian_streaming(project, source, state, save_partial_yaml)

        yaml_content = _normalize_ai_yaml_content(project, state, yaml_content, provider, task.model)
        state = yaml_builder_node(state, project, yaml_content)
        task.progress = 90
        _save_task_progress(db, task, state)

        task.current_node = "schema_validator"
        state = schema_validator_node(state)
        _save_task_progress(db, task, state)
        if state.errors:
            task.current_node = "yaml_repair"
            _save_task_progress(db, task, state)
            repaired_yaml = (
                _build_complete_yaml(project, source, state, "mock", "mock-yaml-repair")
                if provider == "mock"
                else _call_bailian_yaml_repair(project, source, state, yaml_content, state.errors)
            )
            repaired_yaml = _normalize_ai_yaml_content(project, state, repaired_yaml, provider, task.model)
            state = yaml_repair_node(state, repaired_yaml)
            _save_task_progress(db, task, state)

            task.current_node = "schema_validator"
            state = schema_validator_node(state)
            _save_task_progress(db, task, state)
            if state.errors:
                raise ValueError("; ".join(state.errors))
            yaml_content = state.yaml_content or repaired_yaml
        _save_task_progress(db, task, state)

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


def run_generation_task_with_engine(engine: Engine, task_id: int) -> None:
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = SessionLocal()
    try:
        run_generation_task(db, task_id)
    finally:
        db.close()
