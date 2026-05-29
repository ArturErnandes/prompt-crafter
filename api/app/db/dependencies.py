from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.app.db.session import make_session
from api.app.logger import get_logger

logger = get_logger(__name__)

_session_factory: async_sessionmaker | None = None


def init_session_factory() -> None:
    global _session_factory
    _session_factory = make_session()
    logger.info("session_factory инициализирована")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if _session_factory is None:
        raise RuntimeError("session_factory не инициализирована")
    async with _session_factory() as session:
        yield session
