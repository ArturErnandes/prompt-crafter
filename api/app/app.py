from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.app.api.routers import messages, sessions
from api.app.api.ws import session as ws_session
from api.app.config import settings
from api.app.db.dependencies import init_session_factory
from api.app.logger import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging()
    init_session_factory()
    try:
        _app.state.system_prompt = (Path(settings.TEMPLATES_DIR) / "prompting.md").read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error("prompting.md не найден: %s — завершение", Path(settings.TEMPLATES_DIR) / "prompting.md")
        raise RuntimeError("prompting.md not found")
    logger.info("app startup")
    yield
    logger.info("app shutdown")


app = FastAPI(title="prompt-crafter", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(sessions.router)
app.include_router(messages.router)
app.include_router(ws_session.router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
