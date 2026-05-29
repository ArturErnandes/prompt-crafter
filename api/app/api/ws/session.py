from fastapi import APIRouter, Depends, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from api.app.config import settings
from api.app.core.errors import OllamaError
from api.app.db.dependencies import get_session
from api.app.logger import get_logger
from api.app.repositories.messages import MessageRepository
from api.app.repositories.sessions import SessionRepository
from api.app.services.craft import CraftService
from api.app.services.ollama import OllamaService

logger = get_logger(__name__)

router = APIRouter(prefix="/ws/sessions")


@router.websocket("/{session_id}")
async def ws_session(
    websocket: WebSocket,
    session_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    await websocket.accept()
    full_response = ""
    try:
        data = await websocket.receive_json()
        user_message = data.get("content")
        if not user_message:
            await websocket.send_json({"type": "error", "content": "bad_request"})
            await websocket.close(code=1003)
            return

        session_repo = SessionRepository(session)
        message_repo = MessageRepository(session)

        generator = await CraftService(
            OllamaService(settings.OLLAMA_URL, settings.OLLAMA_MODEL, settings.OLLAMA_NUM_CTX),
            session_repo,
            message_repo,
            websocket.app.state.system_prompt,
        ).run(session_id, user_message)

        await message_repo.create(session_id, "user", user_message)

        async for token in generator:
            full_response += token
            await websocket.send_json({"type": "token", "content": token})

        await message_repo.create(session_id, "assistant", full_response)
        await websocket.send_json({"type": "done"})
    except OllamaError as e:
        logger.error("ws_session ollama_error | session_id=%s | error=%s", session_id, str(e))
        if full_response:
            await message_repo.create(session_id, "assistant", full_response)
        await websocket.send_json({"type": "error", "content": str(e)})
        await websocket.close(code=1011)
    except Exception as e:
        logger.error("ws_session error | session_id=%s | error=%s", session_id, str(e))
        await websocket.send_json({"type": "error", "content": "internal_error"})
        await websocket.close(code=1011)
