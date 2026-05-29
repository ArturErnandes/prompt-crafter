from sqlalchemy import text, RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.core.errors import NotFoundError, RepositoryError
from api.app.logger import get_logger

logger = get_logger(__name__)


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, session_id: str, role: str, content: str) -> str:
        logger.info("Создание сообщения | session_id=%s | role=%s", session_id, role)
        try:
            result = await self._session.execute(
                text(
                    "INSERT INTO messages (session_id, role, content)"
                    " VALUES (:session_id, :role, :content) RETURNING id"
                ),
                {"session_id": session_id, "role": role, "content": content},
            )
            row = result.mappings().one()
            result_upd = await self._session.execute(
                text("UPDATE sessions SET updated_at = NOW() WHERE id = :session_id"),
                {"session_id": session_id},
            )
            rows_updated = result_upd.rowcount
            await self._session.commit()
        except Exception as e:
            logger.error("Ошибка создания сообщения | session_id=%s | error=%s", session_id, str(e))
            raise RepositoryError(f"create: {e}") from e

        if rows_updated == 0:
            logger.warning("Сессия не найдена при создании сообщения | session_id=%s", session_id)
            raise NotFoundError(f"session_not_found session_id={session_id}")
        return str(row["id"])

    async def list_by_session(self, session_id: str) -> list[RowMapping]:
        logger.info("Запрос сообщений сессии | session_id=%s", session_id)
        try:
            result = await self._session.execute(
                text("SELECT * FROM messages WHERE session_id = :session_id ORDER BY created_at"),
                {"session_id": session_id},
            )
            return result.mappings().all()
        except Exception as e:
            logger.error("Ошибка запроса сообщений | session_id=%s | error=%s", session_id, str(e))
            raise RepositoryError(f"list_by_session: {e}") from e
