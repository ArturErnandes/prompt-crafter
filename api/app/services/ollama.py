import json
from collections.abc import AsyncGenerator

import httpx

from api.app.core.errors import OllamaError
from api.app.logger import get_logger

logger = get_logger(__name__)


class OllamaService:
    def __init__(self, url: str, model: str, num_ctx: int) -> None:
        self._url = url
        self._model = model
        self._num_ctx = num_ctx

    async def chat(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        logger.info("Запрос к Ollama | model=%s | messages=%s", self._model, len(messages))
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=5.0, read=300.0, write=10.0, pool=5.0)
            ) as client:
                async with client.stream(
                    "POST",
                    f"{self._url}/api/chat",
                    json={
                        "model": self._model,
                        "messages": messages,
                        "stream": True,
                        "options": {"num_ctx": self._num_ctx},
                    },
                ) as response:
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        data = json.loads(line)
                        if data.get("error"):
                            raise OllamaError(f"ollama error: {data['error']}")
                        if data.get("done"):
                            break
                        content = data["message"]["content"]
                        if content:
                            yield content
        except OllamaError:
            raise
        except (httpx.HTTPError, json.JSONDecodeError, KeyError) as e:
            logger.error("Ошибка запроса к Ollama | model=%s | error=%s", self._model, str(e))
            raise OllamaError(f"chat: {e}") from e
