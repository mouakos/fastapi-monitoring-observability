"""Loguru-based logging configuration for the FastAPI application.

Responsibilities of this module:
- Define the shared log format used by all sinks.
- Expose a patcher registry so other modules can inject context into every log record
  without coupling those modules to each other.
- Bridge the standard-library logging into Loguru so all logs are captured in a single pipeline.
- Configure sinks (stdout, optional rotating file) and silence noisy loggers.
"""

import logging
import sys
from collections.abc import Callable
from typing import Any

from loguru import logger

from app.settings import config

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Format for logs using UTC timestamps
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss!UTC}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level> - "
    "<yellow>{extra}</yellow>"
)

# Loggers to silence (they are noisy and handled by our own middleware)

# ---------------------------------------------------------------------------
# Patcher registry — lets multiple modules register log record patchers
# ---------------------------------------------------------------------------

_patchers: list[Callable[[dict[str, Any]], None]] = []


def register_log_patcher(fn: Callable[[dict[str, Any]], None]) -> None:
    """Add a patcher function to the global Loguru patcher registry.

    Patchers are called on every log record before it is forwarded to any sink.
    Use this to inject context (e.g. request_id, trace_id) into
    record["extra"] from a ContextVar or any other source.

    Patchers are applied in registration order. Registering the same function
    multiple times will cause it to run multiple times.

    Args:
        fn: A callable that accepts a Loguru record dict and mutates it in place.
    """
    _patchers.append(fn)


def _dispatch_patchers(record: dict[str, Any]) -> None:
    """Run all registered patchers on a single Loguru log record.

    Args:
        record: The Loguru log record to mutate.
    """
    for patcher in _patchers:
        patcher(record)


# ---------------------------------------------------------------------------
# Standard-library logging bridge
# ---------------------------------------------------------------------------


class InterceptHandler(logging.Handler):
    """Stdlib logging handler that redirects all records into Loguru.

    Installed as the sole handler on the root logger so that libraries using
    the standard logging module (uvicorn, SQLAlchemy, httpx, …) are captured
    by Loguru's pipeline and formatted/exported consistently with application logs.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Forward a stdlib LogRecord to the equivalent Loguru level.

        Args:
            record: The stdlib log record to forward.
        """
        level: str | int
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


# ---------------------------------------------------------------------------
# Private setup helpers
# ---------------------------------------------------------------------------


def _setup_sinks(log_level: str) -> None:
    """Attach output sinks to Loguru.

    Args:
        log_level: Minimum log level string (e.g. "INFO", "DEBUG").
    """
    logger.add(
        sys.stdout,
        level=log_level,
        enqueue=True,
        backtrace=False,
        diagnose=False,
        format=LOG_FORMAT,
        serialize=config.log_serialized,
    )

    if config.log_to_file:
        logger.add(
            "logs/app.log",
            level=log_level,
            rotation="5 MB",
            retention=5,
            compression="zip",
            enqueue=True,
            backtrace=False,
            diagnose=False,
            format=LOG_FORMAT,
            serialize=config.log_serialized,
        )


def _disable_loggers(names: list[str]) -> None:
    """Fully disable a list of stdlib loggers.

    Args:
        names: Logger names to disable.
    """
    for name in names:
        log = logging.getLogger(name)
        log.handlers = []
        log.propagate = False
        log.disabled = True


def _intercept_standard_logging(log_level: str) -> None:
    """Route stdlib logging into Loguru.

    Replaces all root logger handlers with a single InterceptHandler so every
    stdlib log record is forwarded to Loguru.

    Args:
        log_level: Minimum log level string applied to the root logger.
    """
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(log_level)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def setup_logging(silenced_loggers: list[str] | None = None) -> None:
    """Initialise the Loguru logging pipeline.

    Must be called once at application startup, before any other module logs.
    Performs the following steps in order:
    1. Remove Loguru's default stderr handler.
    2. Configure the global patcher dispatcher and default extra fields
       (version, environment) shared across all log records.
    3. Add output sinks (stdout + optional rotating file).
    4. Bridge stdlib logging into Loguru.
    5. Disable any loggers passed via silenced_loggers.

    Args:
        silenced_loggers: Optional list of stdlib logger names to disable entirely. Defaults to None (no loggers silenced).
    """
    log_level = config.log_level.upper()

    logger.remove()
    logger.configure(
        patcher=_dispatch_patchers,  # type: ignore[arg-type]
        extra={"version": config.api_version, "environment": config.environment},
    )

    _setup_sinks(log_level)
    _intercept_standard_logging(log_level)
    if silenced_loggers:
        _disable_loggers(silenced_loggers)
