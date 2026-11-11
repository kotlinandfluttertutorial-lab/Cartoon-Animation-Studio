"""Structured logging factory for the Local 3D Cartoon Animation Studio."""
from __future__ import annotations
import logging
import logging.handlers
from pathlib import Path

_LOGS_DIR: Path | None = None
_loggers: dict[str, logging.Logger] = {}

_LOG_FILES = {
    "app": "app.log",
    "blender": "blender.log",
    "ffmpeg": "ffmpeg.log",
    "jobs": "jobs.log",
    "errors": "errors.log",
}


def configure_logging(logs_dir: str | Path) -> None:
    """Configure the log directory. Call once at startup."""
    global _LOGS_DIR
    _LOGS_DIR = Path(logs_dir)
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)
    _loggers.clear()


def get_logger(name: str) -> logging.Logger:
    """Return a logger for *name*. Writes to logs/<name>.log and to stderr."""
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(f"studio.{name}")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # Console handler — only add if not already present
    if not any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        for h in logger.handlers
    ):
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(fmt)
        logger.addHandler(ch)

    # File handler
    if _LOGS_DIR is not None:
        log_file_name = _LOG_FILES.get(name, f"{name}.log")
        log_path = _LOGS_DIR / log_file_name
        fh = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=10 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

        # Also write errors to errors.log
        if name != "errors":
            err_path = _LOGS_DIR / "errors.log"
            eh = logging.handlers.RotatingFileHandler(
                err_path, maxBytes=10 * 1024 * 1024, backupCount=3, encoding="utf-8"
            )
            eh.setLevel(logging.ERROR)
            eh.setFormatter(fmt)
            logger.addHandler(eh)

    logger.propagate = False
    _loggers[name] = logger
    return logger
