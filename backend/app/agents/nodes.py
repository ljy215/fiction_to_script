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
            "order": chapter["order"],
            "title": chapter["title"],
            "summary": str(chapter["content"])[:120].replace("\n", " "),
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
                "order": summary["order"],
                "summary": summary["summary"],
                "participants": ["char_001"],
                "location_id": "loc_001",
                "consequence": "推动主人公继续行动。",
            }
        )
    state.events = events
    state.finish_node("event_extractor")
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
