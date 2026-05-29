from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.api.schemas.sessions import SessionCreateResponse, SessionResponse
from api.app.core.errors import RepositoryError
from api.app.db.dependencies import get_session
from api.app.logger import get_logger
from api.app.repositories.sessions import SessionRepository

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions"])


@router.post("", response_model=SessionCreateResponse)
async def create_session(session: AsyncSession = Depends(get_session)) -> SessionCreateResponse:
    try:
        repo = SessionRepository(session)
        row = await repo.create(user_id=1, template_name="default")
        return SessionCreateResponse(**row)
    except RepositoryError as e:
        logger.error("create_session db_error | error=%s", str(e))
        raise HTTPException(status_code=500, detail="db_error")
    except Exception as e:
        logger.error("create_session error | error=%s", str(e))
        raise HTTPException(status_code=500, detail="internal_error")


@router.get("", response_model=list[SessionResponse])
async def list_sessions(session: AsyncSession = Depends(get_session)) -> list[SessionResponse]:
    try:
        repo = SessionRepository(session)
        rows = await repo.list_by_user(user_id=1)
        return [SessionResponse(**row) for row in rows]
    except RepositoryError as e:
        logger.error("list_sessions db_error | error=%s", str(e))
        raise HTTPException(status_code=500, detail="db_error")
    except Exception as e:
        logger.error("list_sessions error | error=%s", str(e))
        raise HTTPException(status_code=500, detail="internal_error")
