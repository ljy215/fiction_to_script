from datetime import datetime, timezone
import json
import re

import yaml

from app.config import get_settings
from app.schemas import ScriptPartialRegenerationCreate
from app.services.bailian_client import BailianChatMessage, BailianClient, is_mock_bailian_api_key
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


def _clean_json_content(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _load_json_patch(content: str) -> dict[str, object]:
    try:
        payload = json.loads(_clean_json_content(content))
    except ValueError as exc:
        raise ValueError("AI partial regeneration did not return valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("AI partial regeneration JSON must be an object")
    return payload


def _characters_for_prompt(document: dict[str, object]) -> list[dict[str, object]]:
    characters = document.get("characters")
    if not isinstance(characters, list):
        return []
    return [
        {
            "id": character.get("id"),
            "name": character.get("name"),
            "role": character.get("role"),
            "description": character.get("description"),
        }
        for character in characters
        if isinstance(character, dict)
    ]


def _line_for_prompt(line: dict[str, object]) -> dict[str, object]:
    return {
        "id": line.get("id"),
        "type": line.get("type"),
        "character_id": line.get("character_id"),
        "speaker": line.get("speaker"),
        "text": line.get("text") or line.get("content"),
    }


def _scene_for_prompt(scene: dict[str, object], lines: list[dict[str, object]]) -> dict[str, object]:
    return {
        "id": scene.get("id"),
        "heading": scene.get("heading"),
        "purpose": scene.get("purpose"),
        "conflict": scene.get("conflict"),
        "outcome": scene.get("outcome"),
        "lines": [_line_for_prompt(line) for line in lines],
    }


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
            "id": f"note_regen_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            "target_id": target_id,
            "level": "suggestion",
            "text": f"已局部重生成：{instruction}",
        }
    )


def _apply_line_patch(line: dict[str, object], patch: dict[str, object], valid_character_ids: set[str]) -> None:
    text = patch.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("AI line regeneration must return non-empty text")
    line["text"] = text.strip()
    if "content" in line:
        line["content"] = text.strip()

    character_id = patch.get("character_id")
    if isinstance(character_id, str) and character_id in valid_character_ids:
        line["character_id"] = character_id

    speaker = patch.get("speaker")
    if isinstance(speaker, str) and speaker.strip():
        line["speaker"] = speaker.strip()


def _call_bailian_for_patch(prompt: str) -> dict[str, object]:
    content = BailianClient.from_settings().chat_completion(
        messages=[
            BailianChatMessage(role="system", content="你是中文剧本局部重写助手。只输出 JSON，不要 Markdown，不要解释。"),
            BailianChatMessage(role="user", content=prompt),
        ],
        temperature=0.55,
    )
    return _load_json_patch(content)


def _regenerate_line_with_ai(
    document: dict[str, object],
    scene: dict[str, object],
    line: dict[str, object],
    instruction: str,
) -> dict[str, object]:
    prompt = (
        "请根据上下文重新生成指定剧本行，只改写这一行。\n"
        "必须忠实当前场景、人物关系和原事件，不要改动 ID。\n"
        "只输出 JSON 对象，格式：{\"text\":\"...\",\"speaker\":\"...\",\"character_id\":\"...\"}。\n"
        "如果不是对白行，speaker 和 character_id 可以沿用原值或为空。\n\n"
        f"用户要求：{instruction}\n\n"
        f"可用角色：\n{json.dumps(_characters_for_prompt(document), ensure_ascii=False, indent=2)}\n\n"
        f"场景上下文：\n{json.dumps(_scene_for_prompt(scene, [line]), ensure_ascii=False, indent=2)}"
    )
    return _call_bailian_for_patch(prompt)


def _regenerate_scene_with_ai(
    document: dict[str, object],
    scene: dict[str, object],
    lines: list[dict[str, object]],
    instruction: str,
) -> dict[str, object]:
    prompt = (
        "请根据上下文重新生成指定场景的剧本内容，只改写这个场景。\n"
        "必须保留所有原有 line id 和 line type，不得新增、删除或改名 ID；未选中场景不会被修改。\n"
        "动作行要补足背景、动作、环境和调度；对白要保留人物意图并更适合剧本表达。\n"
        "只输出 JSON 对象，格式：{\"purpose\":\"...\",\"conflict\":\"...\",\"outcome\":\"...\",\"lines\":[{\"id\":\"line_id\",\"text\":\"...\",\"speaker\":\"...\",\"character_id\":\"...\"}]}。\n"
        "lines 必须包含当前场景的全部 line id。\n\n"
        f"用户要求：{instruction}\n\n"
        f"可用角色：\n{json.dumps(_characters_for_prompt(document), ensure_ascii=False, indent=2)}\n\n"
        f"场景上下文：\n{json.dumps(_scene_for_prompt(scene, lines), ensure_ascii=False, indent=2)}"
    )
    return _call_bailian_for_patch(prompt)


def _regenerate_with_mock_rules(
    document: dict[str, object],
    scene: dict[str, object],
    lines: list[dict[str, object]],
    payload: ScriptPartialRegenerationCreate,
    instruction: str,
) -> None:
    if payload.target_type == "line":
        if not payload.line_id:
            raise ValueError("line_id is required for line regeneration")
        for line in lines:
            if isinstance(line, dict) and line.get("id") == payload.line_id:
                line["text"] = _rewrite_line_text(line, scene, instruction)
                if "content" in line:
                    line["content"] = line["text"]
                _append_regeneration_note(document, payload.line_id, instruction)
                break
        else:
            raise ValueError(f"Line not found: {payload.line_id}")
    else:
        for line in lines:
            if isinstance(line, dict):
                line["text"] = _rewrite_line_text(line, scene, instruction)
                if "content" in line:
                    line["content"] = line["text"]
        scene["purpose"] = f"{scene.get('purpose') or '呈现原文事件'}；局部重生成后强化：{instruction}"
        _append_regeneration_note(document, payload.scene_id, instruction)


def _regenerate_with_ai(
    document: dict[str, object],
    scene: dict[str, object],
    lines: list[dict[str, object]],
    payload: ScriptPartialRegenerationCreate,
    instruction: str,
) -> None:
    valid_character_ids = {
        str(character.get("id"))
        for character in (document.get("characters") or [])
        if isinstance(character, dict) and character.get("id")
    }
    if payload.target_type == "line":
        if not payload.line_id:
            raise ValueError("line_id is required for line regeneration")
        for line in lines:
            if isinstance(line, dict) and line.get("id") == payload.line_id:
                patch = _regenerate_line_with_ai(document, scene, line, instruction)
                _apply_line_patch(line, patch, valid_character_ids)
                _append_regeneration_note(document, payload.line_id, instruction)
                break
        else:
            raise ValueError(f"Line not found: {payload.line_id}")
        return

    patch = _regenerate_scene_with_ai(document, scene, lines, instruction)
    for key in ("purpose", "conflict", "outcome"):
        value = patch.get(key)
        if isinstance(value, str) and value.strip():
            scene[key] = value.strip()

    patched_lines = patch.get("lines")
    if not isinstance(patched_lines, list) or not patched_lines:
        raise ValueError("AI scene regeneration must return lines")

    patches_by_id = {
        str(item.get("id")): item
        for item in patched_lines
        if isinstance(item, dict) and item.get("id")
    }
    missing_ids = [str(line.get("id")) for line in lines if isinstance(line, dict) and line.get("id") not in patches_by_id]
    if missing_ids:
        raise ValueError(f"AI scene regeneration missed line ids: {', '.join(missing_ids)}")

    for line in lines:
        if isinstance(line, dict) and line.get("id") in patches_by_id:
            _apply_line_patch(line, patches_by_id[str(line["id"])], valid_character_ids)
    _append_regeneration_note(document, payload.scene_id, instruction)


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

    settings = get_settings()
    if is_mock_bailian_api_key(settings.bailian_api_key):
        _regenerate_with_mock_rules(document, scene, lines, payload, instruction)
    else:
        _regenerate_with_ai(document, scene, lines, payload, instruction)

    document_payload = document.setdefault("document", {})
    if isinstance(document_payload, dict):
        document_payload["updated_at"] = datetime.now(timezone.utc).isoformat()

    next_yaml = yaml.safe_dump(document, allow_unicode=True, sort_keys=False, width=120)
    validation = validate_script_yaml(next_yaml)
    if not validation["valid"]:
        raise ValueError("; ".join(f"{error['path']}: {error['message']}" for error in validation["errors"]))
    return next_yaml
