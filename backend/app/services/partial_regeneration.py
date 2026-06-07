from datetime import datetime, timezone

import yaml

from app.schemas import ScriptPartialRegenerationCreate
from app.services.script_validation import validate_script_yaml


def _target_instruction(instruction: str | None) -> str:
    cleaned = (instruction or "").strip()
    return cleaned or "保持原文事件和人物意图，补强动作、环境和情绪表达。"


def _rewrite_line_text(line: dict[str, object], scene: dict[str, object], instruction: str) -> str:
    original = str(line.get("text") or "").strip()
    line_type = str(line.get("type") or "action")
    heading = str(scene.get("heading") or "当前场景")
    purpose = str(scene.get("purpose") or "推动场景目标")

    if line_type == "dialogue":
        speaker = str(line.get("speaker") or "角色")
        return f"{speaker}压住情绪，把话说得更明确：“{original or purpose}”"
    if line_type == "sound":
        return f"{heading}的声音层次被重新整理：{original or '环境声逐渐压近'}，并服务于{purpose}。"
    if line_type == "narration":
        return f"旁白重新聚焦：{original or purpose}。{instruction}"
    if line_type == "transition":
        return original or "切至："
    return f"{heading}中，{original or purpose}。{instruction}"


def _find_scene(payload: dict[str, object], scene_id: str) -> dict[str, object] | None:
    scenes = payload.get("script", {}).get("scenes", []) if isinstance(payload.get("script"), dict) else []
    if not isinstance(scenes, list):
        return None
    for scene in scenes:
        if isinstance(scene, dict) and scene.get("id") == scene_id:
            return scene
    return None


def _append_regeneration_note(payload: dict[str, object], target_id: str, instruction: str) -> None:
    notes = payload.setdefault("notes", [])
    if not isinstance(notes, list):
        payload["notes"] = []
        notes = payload["notes"]
    notes.append(
        {
            "id": f"note_regen_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "target_id": target_id,
            "level": "suggestion",
            "text": f"已局部重生成：{instruction}",
        }
    )


def regenerate_script_yaml(yaml_content: str, payload: ScriptPartialRegenerationCreate) -> str:
    document = yaml.safe_load(yaml_content)
    if not isinstance(document, dict):
        raise ValueError("YAML root must be an object")

    instruction = _target_instruction(payload.instruction)
    scene = _find_scene(document, payload.scene_id)
    if scene is None:
        raise ValueError(f"Scene not found: {payload.scene_id}")

    lines = scene.get("lines")
    if not isinstance(lines, list):
        raise ValueError(f"Scene has no editable lines: {payload.scene_id}")

    if payload.target_type == "line":
        if not payload.line_id:
            raise ValueError("line_id is required for line regeneration")
        for line in lines:
            if isinstance(line, dict) and line.get("id") == payload.line_id:
                line["text"] = _rewrite_line_text(line, scene, instruction)
                _append_regeneration_note(document, payload.line_id, instruction)
                break
        else:
            raise ValueError(f"Line not found: {payload.line_id}")
    else:
        for line in lines:
            if isinstance(line, dict):
                line["text"] = _rewrite_line_text(line, scene, instruction)
        scene["purpose"] = f"{scene.get('purpose') or '呈现原文事件'}；局部重生成后强化：{instruction}"
        _append_regeneration_note(document, payload.scene_id, instruction)

    document_payload = document.setdefault("document", {})
    if isinstance(document_payload, dict):
        document_payload["updated_at"] = datetime.now(timezone.utc).isoformat()

    next_yaml = yaml.safe_dump(document, allow_unicode=True, sort_keys=False, width=120)
    validation = validate_script_yaml(next_yaml)
    if not validation["valid"]:
        raise ValueError("; ".join(f"{error['path']}: {error['message']}" for error in validation["errors"]))
    return next_yaml
