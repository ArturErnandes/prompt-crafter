import logging
import os
import sys
from pathlib import Path

LOG_FILE_PATH = Path(__file__).resolve().parents[2] / "logs" / "api.log"


def _has_stream_stdout_handler(root: logging.Logger) -> bool:
    for handler in root.handlers:
        if isinstance(handler, logging.StreamHandler) and getattr(handler, "stream", None) is sys.stdout:
            return True
    return False


def _has_file_handler(root: logging.Logger, file_path: Path) -> bool:
    file_path_resolved = file_path.resolve()
    for handler in root.handlers:
        if isinstance(handler, logging.FileHandler):
            base = getattr(handler, "baseFilename", None)
            if isinstance(base, (str, os.PathLike)) and Path(base).resolve() == file_path_resolved:
                return True
    return False


def _resolve_log_level() -> int:
    raw = os.getenv("LOG_LEVEL", "INFO").strip()
    if not raw:
        return logging.INFO
    if raw.isdigit():
        return int(raw)
    level = getattr(logging, raw.upper(), None)
    if isinstance(level, int):
        return level
    return logging.INFO


def setup_logging():
    log_level = _resolve_log_level()
    root = logging.getLogger()
    root.setLevel(log_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | file: %(name)s | func: %(funcName)s | %(message)s",
        datefmt="%d-%m-%Y %H:%M:%S",
    )

    if not _has_stream_stdout_handler(root):
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(log_level)
        root.addHandler(stream_handler)
    else:
        for handler in root.handlers:
            if isinstance(handler, logging.StreamHandler) and getattr(handler, "stream", None) is sys.stdout:
                handler.setLevel(log_level)

    LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _has_file_handler(root, LOG_FILE_PATH):
        file_handler = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        root.addHandler(file_handler)
    else:
        target = LOG_FILE_PATH.resolve()
        for handler in root.handlers:
            if isinstance(handler, logging.FileHandler):
                base = getattr(handler, "baseFilename", None)
                if isinstance(base, (str, os.PathLike)) and Path(base).resolve() == target:
                    handler.setLevel(log_level)
                    handler.setFormatter(formatter)


def get_logger(name: str):
    return logging.getLogger(name)
