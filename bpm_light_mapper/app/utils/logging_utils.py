from __future__ import annotations

import logging
import tempfile
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOG_DIR = Path(__file__).resolve().parents[3] / "logs"
LOG_FILE = LOG_DIR / "bpm_light_mapper.log"
FALLBACK_LOG_FILE = Path(tempfile.gettempdir()) / "bpm_light_mapper.log"


def timestamped(message: str) -> str:
    now = datetime.now().strftime("%H:%M:%S")
    return f"[{now}] {message}"


def setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(exist_ok=True)
    logger = logging.getLogger("bpm_light_mapper")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(threadName)s | %(name)s | %(message)s"
    )

    log_file = LOG_FILE
    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=1_000_000,
            backupCount=5,
            encoding="utf-8",
        )
    except OSError:
        log_file = FALLBACK_LOG_FILE
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=1_000_000,
            backupCount=5,
            encoding="utf-8",
        )
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.propagate = False
    logger.info("Logging initialized. File: %s", log_file)
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    base = setup_logging()
    if not name:
        return base
    return base.getChild(name)


def install_exception_hooks() -> None:
    logger = get_logger("exceptions")

    def handle_exception(exc_type, exc_value, exc_traceback) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.exception("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception

    if hasattr(sys, "unraisablehook"):
        def handle_unraisable(unraisable) -> None:
            logger.exception(
                "Unraisable exception: %s",
                unraisable.err_msg or "unknown",
                exc_info=(type(unraisable.exc_value), unraisable.exc_value, unraisable.exc_traceback),
            )

        sys.unraisablehook = handle_unraisable


@contextmanager
def log_timing(label: str, logger: logging.Logger | None = None):
    active_logger = logger or get_logger("timing")
    start = time.perf_counter()
    active_logger.info("START %s", label)
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        active_logger.info("END %s | %.3fs", label, elapsed)
