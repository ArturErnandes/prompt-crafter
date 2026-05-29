import os
import re

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


def make_session() -> async_sessionmaker:
    raw = os.environ["DATABASE_URL"].replace("postgres://", "postgresql+asyncpg://", 1)
    url = re.sub(r"[?&]sslmode=[^&]*", "", raw).rstrip("?&")
    engine = create_async_engine(url, pool_size=5, max_overflow=10)
    return async_sessionmaker(engine, expire_on_commit=False)
