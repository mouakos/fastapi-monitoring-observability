"""Loguru-based logging configuration for the FastAPI application.

Responsibilities of this module:
- Define the shared log format (LOG_FORMAT) used by all sinks.
- Expose a patcher registry so other modules (otel.py, correlation_id.py, etc.)
  can inject per-request context (trace_id, request_id, …) into every log record
  without coupling those modules to each other.
- Bridge the standard-library logging (used by uvicorn, third-party libs) into
  Loguru via InterceptHandler so all logs are captured in a single pipeline.
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
_SILENCED_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi")

# ---------------------------------------------------------------------------
# Patcher registry — lets multiple modules register log record patchers
# ---------------------------------------------------------------------------

_patchers: list[Callable[[dict[str, Any]], None]] = []


def register_log_patcher(fn: Callable[[dict[str, Any]], None]) -> None:
    """Add a patcher function to the global Loguru patcher registry.

    Patchers are called on every log record before it is forwarded to any sink.
    Use this to inject per-request context (e.g. request_id, trace_id) into
    record["extra"] from a ContextVar or any other source.

    Patchers are applied in registration order. Registering the same function
    multiple times will cause it to run multiple times.

    Args:
        fn: A callable that accepts a Loguru record dict and mutates it in place.
    """
    _patchers.append(fn)


def _dispatch_patchers(record: dict[str, Any]) -> None:
    """Run all registered patchers on a single Loguru log record.

    Passed directly to logger.configure(patcher=...) so Loguru calls it once
    per record. Iterates the registry in insertion order.

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

        Resolves the correct Loguru level name from the stdlib level, then walks
        up the call stack to find the true call site (skipping logging internals)
        so the logged location points at the original caller, not this handler.

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

    Always adds a stdout (console) sink. Adds a rotating file sink at
    logs/app.log when config.log_to_file is True (5 MB rotation, 5 retained
    files, gzip compression).

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


def _intercept_standard_logging(log_level: str) -> None:
    """Route stdlib logging into Loguru and disable noisy third-party loggers.

    Replaces all root logger handlers with a single InterceptHandler so every
    stdlib log record is forwarded to Loguru. Loggers in _SILENCED_LOGGERS
    (uvicorn, fastapi) are disabled because their access/error logs are already
    captured at a higher level by our own middleware.

    Args:
        log_level: Minimum log level string applied to the root logger.
    """
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(log_level)

    for name in _SILENCED_LOGGERS:
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = False
        logging.getLogger(name).disabled = True


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def setup_logging() -> None:
    """Initialise the Loguru logging pipeline.

    Must be called once at application startup, before any other module logs.
    Performs the following steps in order:
    1. Remove Loguru's default stderr handler.
    2. Configure the global patcher dispatcher and default extra fields
       (version, environment) shared across all log records.
    3. Add output sinks (stdout + optional file).
    4. Bridge stdlib logging into Loguru and silence noisy loggers.
    """
    log_level = config.log_level.upper()

    logger.remove()
    logger.configure(
        patcher=_dispatch_patchers,  # type: ignore[arg-type]
        extra={"version": config.api_version, "environment": config.environment},
    )

    _setup_sinks(log_level)
    _intercept_standard_logging(log_level)
