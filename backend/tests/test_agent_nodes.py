import unittest

from app.agents.nodes import (
    chapter_summarizer_node,
    document_parser_node,
    event_extractor_node,
    language_detector_node,
    schema_validator_node,
)
from app.agents.state import GenerationGraphState
from app.models import Chapter, SourceDocument


class AgentNodeTest(unittest.TestCase):
    def test_nodes_advance_state_with_mock_inputs(self):
        source = SourceDocument(
            id=1,
            owner_id=1,
            project_id=1,
            source_type="pasted_text",
            content_text="第一章\n林晚发现线索。",
            content_length=12,
        )
        chapters = [
            Chapter(
                id=1,
                owner_id=1,
                project_id=1,
                source_document_id=1,
                order=1,
                title="第一章",
                content_text="林晚发现线索。",
                content_length=7,
            )
        ]
        state = GenerationGraphState(project_id=1, source_document_id=1)

        state = document_parser_node(state, source, chapters)
        state = language_detector_node(state, source)
        state = chapter_summarizer_node(state)
        state = event_extractor_node(state)

        self.assertEqual(state.source_language, "zh-CN")
        self.assertEqual(state.chapters[0]["title"], "第一章")
        self.assertEqual(state.chapter_summaries[0]["chapter_id"], "ch_001")
        self.assertEqual(state.events[0]["id"], "evt_001")
        self.assertIn("event_extractor", state.completed_nodes)

    def test_schema_validator_records_error_for_empty_yaml(self):
        state = GenerationGraphState(project_id=1, source_document_id=1)

        state = schema_validator_node(state)

        self.assertEqual(state.current_node, "failed")
        self.assertTrue(state.errors)


if __name__ == "__main__":
    unittest.main()
