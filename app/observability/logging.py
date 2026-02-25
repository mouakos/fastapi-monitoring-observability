"""Logging configuration for the FastAPI application using Loguru.

We use Loguru for structured logging and to capture logs from standard logging libraries.
Loguru provides a powerful and flexible logging system that allows us to easily configure log levels, formats, and outputs (console, file, etc.).
By intercepting standard logging, we ensure that all logs from the application and its dependencies are captured in a consistent format.
"""

import logging
import sys

from loguru import logger

from app.settings import config


class InterceptHandler(logging.Handler):
    """Redirect standard logging records to Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        """Redirect standard logging records to Loguru.

        Args:
            record (logging.LogRecord): The log record to be emitted.
        """
        # Get corresponding Loguru level if it exists
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


def setup_logging() -> None:
    """Setup logging configuration using Loguru."""
    log_level = config.log_level.upper()
    log_to_file = config.log_to_file
    serialize = config.log_format.lower() == "json"

    # Remove default Loguru handler
    logger.remove()

    # Format for logs
    text_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level> - "
        "<yellow>{extra}</yellow>"
    )

    # Console sink
    logger.add(
        sys.stdout,
        level=log_level,
        enqueue=True,
        backtrace=False,
        diagnose=False,
        format=text_format,
        serialize=serialize,
    )

    # File sink (rotation)
    if log_to_file:
        logger.add(
            "logs/app.log",
            level=log_level,
            rotation="5 MB",
            retention=5,
            compression="zip",
            enqueue=True,
            backtrace=False,
            diagnose=False,
            format=text_format,
            serialize=serialize,
        )

    # Intercept standard logging (uvicorn, libs, etc.)
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(log_level)

    # Disable default loggers from uvicorn and FastAPI to avoid duplicate logs
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = False
        logging.getLogger(name).disabled = True
