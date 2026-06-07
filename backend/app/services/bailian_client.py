from dataclasses import dataclass
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
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_key = api_key.strip()
        self._model = model
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
        except httpx.HTTPStatusError as exc:
            raise BailianClientError(
                f"Bailian request failed with HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise BailianClientError("Bailian request failed") from exc

        payload = _response_json(response)
        return _extract_message_content(payload)


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
