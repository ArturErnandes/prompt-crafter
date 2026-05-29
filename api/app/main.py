import uvicorn

from api.app.config import settings
from api.app.logger import get_logger, setup_logging

logger = get_logger(__name__)


def main() -> None:
    setup_logging()
    host = settings.APP_HOST
    port = settings.APP_PORT
    try:
        logger.info("app запущен | host=%s | port=%s", host, port)
        uvicorn.run("api.app.app:app", host=host, port=port)
    except Exception as e:
        logger.error("app ошибка запуска | error=%s", str(e))
        raise


if __name__ == "__main__":
    main()
