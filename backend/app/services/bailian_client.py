from dataclasses import dataclass
import json
import time
from typing import Any

import httpx

from app.config import Settings, get_settings


MOCK_BAILIAN_API_KEYS = {"", "mock", "dev-placeholder-bailian-api-key"}


class BailianClientError(RuntimeError):
    """Raised when Bailian cannot return usable model content."""


@dataclass(frozen=True)
class BailianChatMessage:
    role: str
    content: str

    def as_payload(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


def is_mock_bailian_api_key(api_key: str | None) -> bool:
    return (api_key or "").strip().lower() in MOCK_BAILIAN_API_KEYS


class BailianClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float = 90,
        max_retries: int = 2,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_key = api_key.strip()
        self._model = model
        self._max_retries = max_retries
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            transport=transport,
        )

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "BailianClient":
        configured = settings or get_settings()
        return cls(
            api_key=configured.bailian_api_key,
            base_url=configured.bailian_base_url,
            model=configured.bailian_model,
        )

    def chat_completion(self, messages: list[BailianChatMessage], temperature: float = 0.4) -> str:
        if is_mock_bailian_api_key(self._api_key):
            raise BailianClientError("Bailian API key is not configured for real model calls")

        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.post(
                    "/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={
                        "model": self._model,
                        "messages": [message.as_payload() for message in messages],
                        "temperature": temperature,
                    },
                )
                response.raise_for_status()
                break
            except httpx.HTTPStatusError as exc:
                raise BailianClientError(
                    f"Bailian request failed with HTTP {exc.response.status_code}"
                ) from exc
            except httpx.HTTPError as exc:
                if attempt >= self._max_retries:
                    raise BailianClientError(f"Bailian request failed: {type(exc).__name__}: {exc}") from exc
                time.sleep(1.5 * (attempt + 1))

        payload = _response_json(response)
        return _extract_message_content(payload)

    def chat_completion_stream(self, messages: list[BailianChatMessage], temperature: float = 0.4):
        if is_mock_bailian_api_key(self._api_key):
            raise BailianClientError("Bailian API key is not configured for real model calls")

        for attempt in range(self._max_retries + 1):
            yielded_content = False
            try:
                with self._client.stream(
                    "POST",
                    "/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={
                        "model": self._model,
                        "messages": [message.as_payload() for message in messages],
                        "temperature": temperature,
                        "stream": True,
                    },
                ) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if not line:
                            continue
                        if line.startswith("data:"):
                            line = line.removeprefix("data:").strip()
                        if line == "[DONE]":
                            return
                        delta = _extract_stream_delta(line)
                        if delta:
                            yielded_content = True
                            yield delta
                    if yielded_content:
                        return
            except httpx.HTTPStatusError as exc:
                raise BailianClientError(
                    f"Bailian request failed with HTTP {exc.response.status_code}"
                ) from exc
            except httpx.HTTPError as exc:
                if yielded_content or attempt >= self._max_retries:
                    raise BailianClientError(f"Bailian request failed: {type(exc).__name__}: {exc}") from exc
                time.sleep(1.5 * (attempt + 1))
                continue

            if attempt >= self._max_retries:
                raise BailianClientError("Bailian streaming response did not contain message content")
            time.sleep(1.5 * (attempt + 1))


def _response_json(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise BailianClientError("Bailian response is not valid JSON") from exc

    if not isinstance(payload, dict):
        raise BailianClientError("Bailian response JSON must be an object")
    return payload


def _extract_message_content(payload: dict[str, Any]) -> str:
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise BailianClientError("Bailian response does not contain message content") from exc

    if not isinstance(content, str) or not content.strip():
        raise BailianClientError("Bailian response message content is empty")
    return content.strip()


def _extract_stream_delta(line: str) -> str:
    try:
        payload = json.loads(line)
    except ValueError as exc:
        raise BailianClientError("Bailian streaming response is not valid JSON") from exc

    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""

    choice = choices[0]
    if not isinstance(choice, dict):
        return ""

    delta = choice.get("delta") or {}
    if not isinstance(delta, dict):
        return ""
    content = delta.get("content")
    if isinstance(content, str):
        return content

    message = choice.get("message") or {}
    if isinstance(message, dict) and isinstance(message.get("content"), str):
        return message["content"]
    return ""
