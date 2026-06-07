from collections.abc import Iterable
from typing import Any
import re

import yaml


ALLOWED_LINE_TYPES = {
    "action",
    "dialogue",
    "narration",
    "sound",
    "transition",
    "stage_direction",
    "note",
}

REQUIRED_ROOT_KEYS = [
    "schema_version",
    "document",
    "source",
    "script_config",
    "generation",
    "characters",
    "locations",
    "events",
    "adaptation",
    "script",
]

SENSITIVE_KEY_PATTERNS = [
    "api_key",
    "apikey",
    "access_key",
    "secret_key",
    "password",
    "passwd",
    "token",
    "jwt",
    "authorization",
    "stack_trace",
    "traceback",
]

SENSITIVE_VALUE_PATTERNS = [
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{10,}", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_-]{16,}", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"Traceback \(most recent call last\):"),
]


def validate_script_yaml(yaml_content: str) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    try:
        payload = yaml.safe_load(yaml_content)
    except yaml.YAMLError as exc:
        return {
            "valid": False,
            "errors": [{"path": "$", "message": f"YAML cannot be parsed: {exc}"}],
        }

    if not isinstance(payload, dict):
        return {
            "valid": False,
            "errors": [{"path": "$", "message": "YAML root must be a mapping object"}],
        }

    _validate_required_root(payload, errors)
    _validate_document(payload, errors)
    _validate_source(payload, errors)
    _validate_script_config(payload, errors)
    _validate_generation(payload, errors)
    _validate_adaptation(payload, errors)
    _validate_collections(payload, errors)
    _validate_references(payload, errors)
    _validate_sensitive_content(payload, "$", errors)

    return {"valid": not errors, "errors": errors}


def _add_error(errors: list[dict[str, str]], path: str, message: str) -> None:
    errors.append({"path": path, "message": message})


def _require_mapping(value: Any, path: str, errors: list[dict[str, str]]) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    _add_error(errors, path, "must be an object")
    return {}


def _require_list(value: Any, path: str, errors: list[dict[str, str]]) -> list[Any]:
    if isinstance(value, list):
        return value
    _add_error(errors, path, "must be a list")
    return []


def _require_keys(mapping: dict[str, Any], path: str, keys: Iterable[str], errors: list[dict[str, str]]) -> None:
    for key in keys:
        if key not in mapping:
            _add_error(errors, f"{path}.{key}", "is required")


def _validate_required_root(payload: dict[str, Any], errors: list[dict[str, str]]) -> None:
    for key in REQUIRED_ROOT_KEYS:
        if key not in payload:
            _add_error(errors, key, "is required")

    script = _require_mapping(payload.get("script"), "script", errors)
    if "scenes" not in script:
        _add_error(errors, "script.scenes", "is required")


def _validate_document(payload: dict[str, Any], errors: list[dict[str, str]]) -> None:
    document = _require_mapping(payload.get("document"), "document", errors)
    _require_keys(document, "document", ["id", "project_id", "title", "status", "created_at", "updated_at"], errors)


def _validate_source(payload: dict[str, Any], errors: list[dict[str, str]]) -> None:
    source = _require_mapping(payload.get("source"), "source", errors)
    _require_keys(
        source,
        "source",
        [
            "novel_title",
            "source_language",
            "output_language",
            "minimum_chapters_required",
            "chapter_count",
            "chapters",
        ],
        errors,
    )

    if source.get("output_language") != "zh-CN":
        _add_error(errors, "source.output_language", 'must be "zh-CN"')

    if source.get("minimum_chapters_required") != 3:
        _add_error(errors, "source.minimum_chapters_required", "must be 3")

    chapters = _require_list(source.get("chapters"), "source.chapters", errors)
    chapter_count = source.get("chapter_count")
    if isinstance(chapter_count, int):
        if chapter_count != len(chapters):
            _add_error(errors, "source.chapter_count", "must match source.chapters length")
        if chapter_count < 3:
            _add_error(errors, "source.chapter_count", "must be at least 3")
    else:
        _add_error(errors, "source.chapter_count", "must be an integer")

    for index, chapter in enumerate(chapters):
        chapter_map = _require_mapping(chapter, f"source.chapters[{index}]", errors)
        _require_keys(chapter_map, f"source.chapters[{index}]", ["id", "order", "title", "summary"], errors)


def _validate_script_config(payload: dict[str, Any], errors: list[dict[str, str]]) -> None:
    script_config = _require_mapping(payload.get("script_config"), "script_config", errors)
    _require_keys(
        script_config,
        "script_config",
        ["script_type", "script_type_label", "fidelity_policy", "output_mode"],
        errors,
    )


def _validate_generation(payload: dict[str, Any], errors: list[dict[str, str]]) -> None:
    generation = _require_mapping(payload.get("generation"), "generation", errors)
    _require_keys(generation, "generation", ["provider", "model", "generated_at"], errors)


def _validate_adaptation(payload: dict[str, Any], errors: list[dict[str, str]]) -> None:
    adaptation = _require_mapping(payload.get("adaptation"), "adaptation", errors)
    _require_keys(adaptation, "adaptation", ["logline", "theme", "strategy"], errors)
    strategy = _require_mapping(adaptation.get("strategy"), "adaptation.strategy", errors)
    _require_keys(
        strategy,
        "adaptation.strategy",
        ["preserved_events", "merged_events", "omitted_events", "added_bridges"],
        errors,
    )


def _validate_collections(payload: dict[str, Any], errors: list[dict[str, str]]) -> None:
    characters = _require_list(payload.get("characters"), "characters", errors)
    locations = _require_list(payload.get("locations"), "locations", errors)
    events = _require_list(payload.get("events"), "events", errors)
    scenes = _require_list(_require_mapping(payload.get("script"), "script", errors).get("scenes"), "script.scenes", errors)

    _validate_id_collection(characters, "characters", ["id", "name", "role"], errors)
    _validate_id_collection(locations, "locations", ["id", "name", "type"], errors)
    _validate_id_collection(events, "events", ["id", "chapter_id", "order", "summary", "participants", "location_id"], errors)
    _validate_id_collection(scenes, "script.scenes", ["id", "order", "heading", "location_id", "source_refs", "lines"], errors)

    all_ids: dict[str, str] = {}
    for collection_path, collection in [
        ("source.chapters", _require_list(_require_mapping(payload.get("source"), "source", errors).get("chapters"), "source.chapters", errors)),
        ("characters", characters),
        ("locations", locations),
        ("events", events),
        ("script.scenes", scenes),
    ]:
        for index, item in enumerate(collection):
            item_map = _require_mapping(item, f"{collection_path}[{index}]", errors)
            item_id = item_map.get("id")
            if isinstance(item_id, str) and item_id:
                if item_id in all_ids:
                    _add_error(errors, f"{collection_path}[{index}].id", f'duplicate id "{item_id}" already used at {all_ids[item_id]}')
                else:
                    all_ids[item_id] = f"{collection_path}[{index}].id"

    for scene_index, scene in enumerate(scenes):
        scene_map = _require_mapping(scene, f"script.scenes[{scene_index}]", errors)
        lines = _require_list(scene_map.get("lines"), f"script.scenes[{scene_index}].lines", errors)
        if not lines:
            _add_error(errors, f"script.scenes[{scene_index}].lines", "must contain at least one line")
        for line_index, line in enumerate(lines):
            line_map = _require_mapping(line, f"script.scenes[{scene_index}].lines[{line_index}]", errors)
            line_path = f"script.scenes[{scene_index}].lines[{line_index}]"
            _require_keys(line_map, line_path, ["id", "type", "text"], errors)
            line_type = line_map.get("type")
            if line_type not in ALLOWED_LINE_TYPES:
                _add_error(errors, f"{line_path}.type", f"must be one of {sorted(ALLOWED_LINE_TYPES)}")
            if line_type == "dialogue" and not line_map.get("character_id"):
                _add_error(errors, f"{line_path}.character_id", "is required for dialogue lines")


def _validate_id_collection(
    collection: list[Any],
    path: str,
    required_keys: list[str],
    errors: list[dict[str, str]],
) -> None:
    seen_ids: set[str] = set()
    for index, item in enumerate(collection):
        item_path = f"{path}[{index}]"
        item_map = _require_mapping(item, item_path, errors)
        _require_keys(item_map, item_path, required_keys, errors)
        item_id = item_map.get("id")
        if not isinstance(item_id, str) or not item_id.strip():
            _add_error(errors, f"{item_path}.id", "must be a non-empty string")
        elif item_id in seen_ids:
            _add_error(errors, f"{item_path}.id", f'duplicate id "{item_id}"')
        else:
            seen_ids.add(item_id)


def _id_set(items: list[Any]) -> set[str]:
    return {item.get("id") for item in items if isinstance(item, dict) and isinstance(item.get("id"), str)}


def _validate_references(payload: dict[str, Any], errors: list[dict[str, str]]) -> None:
    source = _require_mapping(payload.get("source"), "source", errors)
    chapters = _require_list(source.get("chapters"), "source.chapters", errors)
    characters = _require_list(payload.get("characters"), "characters", errors)
    locations = _require_list(payload.get("locations"), "locations", errors)
    events = _require_list(payload.get("events"), "events", errors)
    scenes = _require_list(_require_mapping(payload.get("script"), "script", errors).get("scenes"), "script.scenes", errors)

    chapter_ids = _id_set(chapters)
    character_ids = _id_set(characters)
    location_ids = _id_set(locations)
    event_ids = _id_set(events)

    for event_index, event in enumerate(events):
        event_map = _require_mapping(event, f"events[{event_index}]", errors)
        if event_map.get("chapter_id") not in chapter_ids:
            _add_error(errors, f"events[{event_index}].chapter_id", "must reference an existing chapter id")
        if event_map.get("location_id") not in location_ids:
            _add_error(errors, f"events[{event_index}].location_id", "must reference an existing location id")
        participants = _require_list(event_map.get("participants"), f"events[{event_index}].participants", errors)
        for participant_index, character_id in enumerate(participants):
            if character_id not in character_ids:
                _add_error(
                    errors,
                    f"events[{event_index}].participants[{participant_index}]",
                    "must reference an existing character id",
                )

    for scene_index, scene in enumerate(scenes):
        scene_map = _require_mapping(scene, f"script.scenes[{scene_index}]", errors)
        if scene_map.get("location_id") not in location_ids:
            _add_error(errors, f"script.scenes[{scene_index}].location_id", "must reference an existing location id")

        source_refs = _require_list(scene_map.get("source_refs"), f"script.scenes[{scene_index}].source_refs", errors)
        for ref_index, source_ref in enumerate(source_refs):
            ref_map = _require_mapping(source_ref, f"script.scenes[{scene_index}].source_refs[{ref_index}]", errors)
            if ref_map.get("chapter_id") not in chapter_ids:
                _add_error(
                    errors,
                    f"script.scenes[{scene_index}].source_refs[{ref_index}].chapter_id",
                    "must reference an existing chapter id",
                )
            event_id = ref_map.get("event_id")
            if event_id is not None and event_id not in event_ids:
                _add_error(
                    errors,
                    f"script.scenes[{scene_index}].source_refs[{ref_index}].event_id",
                    "must reference an existing event id",
                )

        lines = _require_list(scene_map.get("lines"), f"script.scenes[{scene_index}].lines", errors)
        for line_index, line in enumerate(lines):
            line_map = _require_mapping(line, f"script.scenes[{scene_index}].lines[{line_index}]", errors)
            if line_map.get("type") == "dialogue" and line_map.get("character_id") not in character_ids:
                _add_error(
                    errors,
                    f"script.scenes[{scene_index}].lines[{line_index}].character_id",
                    "must reference an existing character id",
                )


def _validate_sensitive_content(value: Any, path: str, errors: list[dict[str, str]]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path != "$" else str(key)
            normalized_key = str(key).lower().replace("-", "_")
            if any(pattern in normalized_key for pattern in SENSITIVE_KEY_PATTERNS):
                _add_error(errors, child_path, "must not contain sensitive fields")
            _validate_sensitive_content(child, child_path, errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_sensitive_content(child, f"{path}[{index}]", errors)
    elif isinstance(value, str):
        for pattern in SENSITIVE_VALUE_PATTERNS:
            if pattern.search(value):
                _add_error(errors, path, "must not contain secrets or server stack traces")
                break
