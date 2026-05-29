from collections.abc import AsyncGenerator

from api.app.logger import get_logger
from api.app.repositories.messages import MessageRepository
from api.app.repositories.sessions import SessionRepository
from api.app.services.ollama import OllamaService

logger = get_logger(__name__)


class CraftService:
    def __init__(self, ollama: OllamaService, session_repo: SessionRepository, message_repo: MessageRepository, system_prompt: str) -> None:
        self._ollama = ollama
        self._session_repo = session_repo
        self._message_repo = message_repo
        self._system_prompt = system_prompt

    async def run(self, session_id: str, user_message: str) -> AsyncGenerator[str, None]:
        logger.info("Запуск трансформации | session_id=%s", session_id)
        history = await self._message_repo.list_by_session(session_id)
        messages = [
            {"role": "system", "content": self._system_prompt},
            *[{"role": row["role"], "content": row["content"]} for row in history],
            {"role": "user", "content": user_message},
        ]
        return self._ollama.chat(messages)
