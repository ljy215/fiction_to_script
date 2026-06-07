from app.agents.state import GenerationGraphState
from app.models import Chapter, Project, SourceDocument
from app.services.script_validation import validate_script_yaml


def document_parser_node(
    state: GenerationGraphState,
    source: SourceDocument,
    chapters: list[Chapter],
) -> GenerationGraphState:
    state.start_node("document_parser")
    state.chapters = [
        {
            "id": f"ch_{chapter.order:03d}",
            "database_id": chapter.id,
            "order": chapter.order,
            "title": chapter.title,
            "content": chapter.content_text,
            "content_length": chapter.content_length,
        }
        for chapter in chapters
    ]
    state.finish_node("document_parser")
    return state


def language_detector_node(state: GenerationGraphState, source: SourceDocument) -> GenerationGraphState:
    state.start_node("language_detector")
    sample = source.content_text[:500]
    cjk_count = sum(1 for char in sample if "\u4e00" <= char <= "\u9fff")
    latin_count = sum(1 for char in sample if char.isascii() and char.isalpha())
    state.source_language = "zh-CN" if cjk_count >= latin_count else "en"
    state.finish_node("language_detector")
    return state


def chapter_summarizer_node(state: GenerationGraphState) -> GenerationGraphState:
    state.start_node("chapter_summarizer")
    state.chapter_summaries = [
        {
            "chapter_id": chapter["id"],
            "database_id": chapter["database_id"],
            "order": chapter["order"],
            "title": chapter["title"],
            "summary": f"{chapter['title']}：{str(chapter['content'])[:120].replace(chr(10), ' ')}",
        }
        for chapter in state.chapters
    ]
    state.finish_node("chapter_summarizer")
    return state


def event_extractor_node(state: GenerationGraphState) -> GenerationGraphState:
    state.start_node("event_extractor")
    events = []
    for summary in state.chapter_summaries:
        events.append(
            {
                "id": f"evt_{summary['order']:03d}",
                "chapter_id": summary["chapter_id"],
                "chapter_database_id": summary["database_id"],
                "order": summary["order"],
                "summary": summary["summary"],
                "participants": ["char_001"],
                "location_id": "loc_001",
                "location_name": "主要场景",
                "consequence": "推动主人公继续行动。",
            }
        )
    state.events = events
    state.finish_node("event_extractor")
    return state


def character_location_extractor_node(state: GenerationGraphState) -> GenerationGraphState:
    state.start_node("character_location_extractor")
    text = "\n".join(str(chapter["content"]) for chapter in state.chapters)
    protagonist_name = "主人公"
    for candidate in ("林晚", "旧友", "女主", "男主"):
        if candidate in text:
            protagonist_name = candidate
            break

    state.characters = [
        {
            "id": "char_001",
            "name": protagonist_name,
            "original_name": "" if state.source_language == "zh-CN" else protagonist_name,
            "role": "protagonist",
            "description": "从小说章节和事件中抽取出的核心行动人物。",
        }
    ]
    state.locations = [
        {
            "id": "loc_001",
            "name": "主要场景",
            "original_name": "",
            "type": "mixed",
            "description": "承载前三章主要事件的综合场景。",
        }
    ]
    state.finish_node("character_location_extractor")
    return state


def adaptation_planner_node(state: GenerationGraphState, project: Project) -> GenerationGraphState:
    state.start_node("adaptation_planner")
    title = project.novel_title or project.name
    preserved_events = [event["id"] for event in state.events]
    state.adaptation = {
        "logline": f"{title}的主人公在连续事件中面对核心冲突，并做出关键选择。",
        "theme": "选择、真相与成长",
        "strategy": {
            "preserved_events": preserved_events,
            "merged_events": [],
            "omitted_events": [],
            "added_bridges": ["为连接章节事件补充少量过渡动作。"],
        },
        "notes": ["整体改编以忠实原文事件顺序为优先。"],
    }
    state.finish_node("adaptation_planner")
    return state


def script_writer_node(state: GenerationGraphState) -> GenerationGraphState:
    state.start_node("script_writer")
    character = state.characters[0] if state.characters else {"id": "char_001", "name": "主人公"}
    location = state.locations[0] if state.locations else {"id": "loc_001", "name": "主要场景"}
    scenes = []
    line_order = 1
    for event in state.events:
        scene_order = event["order"]
        scene_id = f"sc_{scene_order:03d}"
        action_line_id = f"line_{line_order:03d}"
        dialogue_line_id = f"line_{line_order + 1:03d}"
        line_order += 2
        scenes.append(
            {
                "id": scene_id,
                "order": scene_order,
                "heading": f"内景 {location['name']} 夜",
                "location_id": location["id"],
                "interior_exterior": "interior",
                "time_of_day": "night",
                "purpose": "呈现原文核心事件并推动人物选择。",
                "conflict": event["summary"],
                "outcome": event["consequence"],
                "source_refs": [
                    {
                        "chapter_id": event["chapter_id"],
                        "event_id": event["id"],
                    }
                ],
                "lines": [
                    {
                        "id": action_line_id,
                        "type": "action",
                        "text": f"{character['name']}进入{location['name']}，事件的压力逐渐显现。",
                    },
                    {
                        "id": dialogue_line_id,
                        "type": "dialogue",
                        "character_id": character["id"],
                        "speaker": character["name"],
                        "text": "这件事不能就这样结束。",
                        "emotion": "坚定",
                    },
                ],
            }
        )
    state.scenes = scenes
    state.finish_node("script_writer")
    return state


def yaml_builder_node(
    state: GenerationGraphState,
    project: Project,
    yaml_content: str,
) -> GenerationGraphState:
    state.start_node("yaml_builder")
    state.script_type = project.script_type
    state.yaml_content = yaml_content
    state.finish_node("yaml_builder")
    return state


def yaml_repair_node(state: GenerationGraphState, repaired_yaml: str) -> GenerationGraphState:
    state.start_node("yaml_repair")
    state.clear_errors()
    state.yaml_content = repaired_yaml
    state.finish_node("yaml_repair")
    return state


def schema_validator_node(state: GenerationGraphState) -> GenerationGraphState:
    state.start_node("schema_validator")
    if not state.yaml_content:
        state.fail("YAML content is empty")
        return state

    result = validate_script_yaml(state.yaml_content)
    if not result["valid"]:
        state.fail("; ".join(f"{error['path']}: {error['message']}" for error in result["errors"]))
        return state

    state.finish_node("schema_validator")
    return state
