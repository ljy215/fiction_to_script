from enum import StrEnum

from pydantic import BaseModel


class ScriptType(StrEnum):
    short_drama = "short_drama"
    film = "film"
    audio_drama = "audio_drama"
    stage_play = "stage_play"


class AgentProfile(BaseModel):
    script_type: ScriptType
    label: str
    graph_name: str
    graph_version: str = "1.0"
    strategy: str
    scene_focus: str
    line_focus: str


SCRIPT_AGENT_PROFILES: dict[ScriptType, AgentProfile] = {
    ScriptType.short_drama: AgentProfile(
        script_type=ScriptType.short_drama,
        label="短剧剧本",
        graph_name="short_drama_script_graph",
        strategy="强调强冲突、快节奏推进和集尾钩子。",
        scene_focus="短场景、高密度反转、明确爽点。",
        line_focus="对白直接、冲突外显、每场保留悬念。",
    ),
    ScriptType.film: AgentProfile(
        script_type=ScriptType.film,
        label="影视剧本",
        graph_name="film_script_graph",
        strategy="强调场景调度、动作、对白和叙事连贯性。",
        scene_focus="视觉化场面、清晰行动线和情绪递进。",
        line_focus="动作与对白平衡，保留镜头可拍性。",
    ),
    ScriptType.audio_drama: AgentProfile(
        script_type=ScriptType.audio_drama,
        label="广播剧剧本",
        graph_name="audio_drama_script_graph",
        strategy="强调对白、旁白、音效和声音表现。",
        scene_focus="用声音建立空间、气氛和人物关系。",
        line_focus="增加旁白、音效提示和语气变化。",
    ),
    ScriptType.stage_play: AgentProfile(
        script_type=ScriptType.stage_play,
        label="舞台剧剧本",
        graph_name="stage_play_script_graph",
        strategy="强调场次、人物出入场、舞台动作和空间调度。",
        scene_focus="舞台空间明确、角色调度可执行。",
        line_focus="对白适合现场表演，动作提示简洁。",
    ),
}


def normalize_script_type(value: str | ScriptType | None) -> ScriptType:
    if value is None or value == "":
        return ScriptType.film
    return ScriptType(value)


def get_agent_profile(value: str | ScriptType | None) -> AgentProfile:
    return SCRIPT_AGENT_PROFILES[normalize_script_type(value)]
