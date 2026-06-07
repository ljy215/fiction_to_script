from typing import Any

from pydantic import BaseModel, Field


class GenerationGraphState(BaseModel):
    project_id: int
    source_document_id: int
    script_type: str | None = None
    source_language: str = "auto"
    output_language: str = "zh-CN"
    current_node: str = "queued"
    completed_nodes: list[str] = Field(default_factory=list)
    chapters: list[dict[str, Any]] = Field(default_factory=list)
    chapter_summaries: list[dict[str, Any]] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    characters: list[dict[str, Any]] = Field(default_factory=list)
    locations: list[dict[str, Any]] = Field(default_factory=list)
    adaptation: dict[str, Any] = Field(default_factory=dict)
    scenes: list[dict[str, Any]] = Field(default_factory=list)
    yaml_content: str | None = None
    errors: list[str] = Field(default_factory=list)

    def start_node(self, node_name: str) -> None:
        self.current_node = node_name

    def finish_node(self, node_name: str) -> None:
        if node_name not in self.completed_nodes:
            self.completed_nodes.append(node_name)
        self.current_node = node_name

    def fail(self, message: str) -> None:
        self.errors.append(message)
        self.current_node = "failed"

    def clear_errors(self) -> None:
        self.errors = []
