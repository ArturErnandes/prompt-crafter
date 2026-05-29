from sqlalchemy import text, RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.core.errors import NotFoundError, RepositoryError
from api.app.logger import get_logger

logger = get_logger(__name__)


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user_id: int, template_name: str) -> RowMapping:
        logger.info("Создание сессии | user_id=%s | template_name=%s", user_id, template_name)
        try:
            result = await self._session.execute(
                text(
                    "INSERT INTO sessions (user_id, template_name) VALUES (:user_id, :template_name)"
                    " RETURNING id, template_name, created_at"
                ),
                {"user_id": user_id, "template_name": template_name},
            )
            row = result.mappings().one()
            await self._session.commit()
        except Exception as e:
            logger.error("Ошибка создания сессии | user_id=%s | error=%s", user_id, str(e))
            raise RepositoryError(f"create: {e}") from e
        return row

    async def get_by_id(self, session_id: str) -> RowMapping:
        logger.info("Запрос сессии | session_id=%s", session_id)
        try:
            result = await self._session.execute(
                text("SELECT * FROM sessions WHERE id = :session_id"),
                {"session_id": session_id},
            )
            row = result.mappings().one_or_none()
        except Exception as e:
            logger.error("Ошибка запроса сессии | session_id=%s | error=%s", session_id, str(e))
            raise RepositoryError(f"get_by_id: {e}") from e

        if row is None:
            logger.warning("Сессия не найдена | session_id=%s", session_id)
            raise NotFoundError(f"session_not_found session_id={session_id}")

        return row

    async def list_by_user(self, user_id: int) -> list[RowMapping]:
        logger.info("Запрос списка сессий | user_id=%s", user_id)
        try:
            result = await self._session.execute(
                text("SELECT * FROM sessions WHERE user_id = :user_id ORDER BY updated_at DESC"),
                {"user_id": user_id},
            )
            return result.mappings().all()
        except Exception as e:
            logger.error("Ошибка запроса списка сессий | user_id=%s | error=%s", user_id, str(e))
            raise RepositoryError(f"list_by_user: {e}") from e

    async def update_title(self, session_id: str, title: str) -> None:
        logger.info("Обновление заголовка сессии | session_id=%s", session_id)
        try:
            result = await self._session.execute(
                text("UPDATE sessions SET title = :title WHERE id = :session_id RETURNING id"),
                {"session_id": session_id, "title": title},
            )
            row = result.mappings().one_or_none()
            await self._session.commit()
        except Exception as e:
            logger.error("Ошибка обновления заголовка | session_id=%s | error=%s", session_id, str(e))
            raise RepositoryError(f"update_title: {e}") from e

        if row is None:
            logger.warning("Сессия не найдена | session_id=%s", session_id)
            raise NotFoundError(f"session_not_found session_id={session_id}")
