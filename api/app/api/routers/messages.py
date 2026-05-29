from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.api.schemas.messages import MessageResponse
from api.app.core.errors import RepositoryError
from api.app.db.dependencies import get_session
from api.app.logger import get_logger
from api.app.repositories.messages import MessageRepository

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/sessions", tags=["Messages"])


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
async def list_messages(session_id: str, session: AsyncSession = Depends(get_session)) -> list[MessageResponse]:
    try:
        repo = MessageRepository(session)
        rows = await repo.list_by_session(session_id)
        return [MessageResponse(**row) for row in rows]
    except RepositoryError as e:
        logger.error("list_messages db_error | session_id=%s | error=%s", session_id, str(e))
        raise HTTPException(status_code=500, detail="db_error")
    except Exception as e:
        logger.error("list_messages error | session_id=%s | error=%s", session_id, str(e))
        raise HTTPException(status_code=500, detail="internal_error")
