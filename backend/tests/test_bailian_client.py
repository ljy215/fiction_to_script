import json
import unittest

import httpx

from app.services.bailian_client import (
    BailianChatMessage,
    BailianClient,
    BailianClientError,
    is_mock_bailian_api_key,
)


class BailianClientTest(unittest.TestCase):
    def test_chat_completion_sends_openai_compatible_request(self):
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["authorization"] = request.headers.get("authorization")
            captured["payload"] = json.loads(request.content.decode("utf-8"))
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "schema_version: \"1.0\""}}]},
            )

        client = BailianClient(
            api_key="test-api-key",
            base_url="https://bailian.example.test/compatible-mode/v1",
            model="qwen-plus",
            transport=httpx.MockTransport(handler),
        )

        content = client.chat_completion(
            messages=[
                BailianChatMessage(role="system", content="system prompt"),
                BailianChatMessage(role="user", content="user prompt"),
            ],
            temperature=0.2,
        )

        self.assertEqual(content, 'schema_version: "1.0"')
        self.assertEqual(
            captured["url"],
            "https://bailian.example.test/compatible-mode/v1/chat/completions",
        )
        self.assertEqual(captured["authorization"], "Bearer test-api-key")
        self.assertEqual(captured["payload"]["model"], "qwen-plus")
        self.assertEqual(captured["payload"]["temperature"], 0.2)
        self.assertEqual(
            captured["payload"]["messages"],
            [
                {"role": "system", "content": "system prompt"},
                {"role": "user", "content": "user prompt"},
            ],
        )

    def test_mock_api_keys_are_detected(self):
        self.assertTrue(is_mock_bailian_api_key(""))
        self.assertTrue(is_mock_bailian_api_key("mock"))
        self.assertTrue(is_mock_bailian_api_key("dev-placeholder-bailian-api-key"))
        self.assertFalse(is_mock_bailian_api_key("test-api-key"))

    def test_mock_key_is_rejected_before_http_request(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError("mock mode must not call the network")

        client = BailianClient(
            api_key="mock",
            base_url="https://bailian.example.test/compatible-mode/v1",
            model="qwen-plus",
            transport=httpx.MockTransport(handler),
        )

        with self.assertRaises(BailianClientError) as caught:
            client.chat_completion(messages=[BailianChatMessage(role="user", content="hello")])

        self.assertIn("not configured", str(caught.exception))

    def test_http_error_does_not_include_api_key_or_response_body(self):
        secret_value = "test-secret-value"

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                401,
                json={"message": f"upstream rejected {secret_value}"},
                request=request,
            )

        client = BailianClient(
            api_key=secret_value,
            base_url="https://bailian.example.test/compatible-mode/v1",
            model="qwen-plus",
            transport=httpx.MockTransport(handler),
        )

        with self.assertRaises(BailianClientError) as caught:
            client.chat_completion(messages=[BailianChatMessage(role="user", content="hello")])

        message = str(caught.exception)
        self.assertIn("HTTP 401", message)
        self.assertNotIn(secret_value, message)
        self.assertNotIn("upstream rejected", message)

    def test_invalid_response_shape_is_rejected(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"choices": []})

        client = BailianClient(
            api_key="test-api-key",
            base_url="https://bailian.example.test/compatible-mode/v1",
            model="qwen-plus",
            transport=httpx.MockTransport(handler),
        )

        with self.assertRaises(BailianClientError) as caught:
            client.chat_completion(messages=[BailianChatMessage(role="user", content="hello")])

        self.assertIn("message content", str(caught.exception))

    def test_streaming_completion_skips_non_content_chunks(self):
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["payload"] = json.loads(request.content.decode("utf-8"))
            body = "\n\n".join(
                [
                    'data: {"choices":[{"delta":{"role":"assistant"}}]}',
                    'data: {"choices":[{"delta":{"content":"schema_"}}]}',
                    'data: {"choices":[{"delta":{"content":"version"}}]}',
                    'data: {"choices":[],"usage":{"total_tokens":12}}',
                    "data: [DONE]",
                ]
            )
            return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

        client = BailianClient(
            api_key="test-api-key",
            base_url="https://bailian.example.test/compatible-mode/v1",
            model="qwen-plus",
            transport=httpx.MockTransport(handler),
        )

        chunks = list(client.chat_completion_stream(messages=[BailianChatMessage(role="user", content="hello")]))

        self.assertEqual(chunks, ["schema_", "version"])
        self.assertTrue(captured["payload"]["stream"])


if __name__ == "__main__":
    unittest.main()
