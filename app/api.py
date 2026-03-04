"""API routes for testing and observability."""

import random
from asyncio import sleep

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException
from loguru import logger
from opentelemetry import context as otel_context
from opentelemetry import trace

from app.settings import config

router = APIRouter()
_tracer = trace.get_tracer(__name__)


@router.get("/", response_model=dict[str, str], summary="Api Root")
def read_root() -> dict[str, str]:
    """Return a welcome message."""
    return {
        "message": "Welcome to the FastAPI application! Please visit /docs for API documentation."
    }


@router.get("/info", response_model=dict[str, str], summary="Application Info")
def app_info() -> dict[str, str]:
    """Return application version and environment."""
    return {"version": config.api_version, "environment": config.environment}


@router.get("/slow", summary="Slow request")
async def slow_endpoint(delay: float = 2.0) -> dict[str, str]:
    """Simulate a slow endpoint by sleeping for a specified duration to test latency monitoring and alerting."""
    await sleep(delay)
    logger.bind(delay=delay).info("slow_endpoint_completed")
    return {"message": f"Response after {delay}s"}


@router.get("/random-status", summary="Random Status")
def random_status() -> dict[str, str]:
    """Return a random HTTP status code (200, 300, 400, or 500) to test error rate monitoring and alerting."""
    status_codes = [200, 200, 300, 400, 500]
    status = random.choice(status_codes)
    if status >= 400:
        logger.bind(status_code=status).warning("random_status_error")
        raise HTTPException(status_code=status, detail=f"Simulated {status} error")
    return {"message": f"Success with status {status}"}


@router.get("/crash", summary="Unhandled Exception")
def crash() -> float:
    """Trigger an unhandled ZeroDivisionError to exercise the global exception handler."""
    return 1 / 0


@router.get("/chain", summary="Distributed Trace Chain")
async def chain() -> dict[str, str]:
    """Simulate a chain of dependent HTTP calls to test distributed tracing across services."""
    async with httpx.AsyncClient() as client:
        await client.get("https://httpbin.org/delay/0.1")
        await client.get("https://httpbin.org/status/200")
    return {
        "message": "Completed a chain of dependent HTTP calls — check Tempo for the distributed trace"
    }


@router.get("/trace-nested", summary="Nested Spans")
async def trace_nested() -> dict[str, str]:
    """Create two child spans to verify parent-child span relationships in Tempo."""
    with _tracer.start_as_current_span("step-1-validate") as span1:
        span1.set_attribute("step", 1)
        logger.bind(step=1).info("trace_nested_step")
        await sleep(0.05)

    with _tracer.start_as_current_span("step-2-process") as span2:
        span2.set_attribute("step", 2)
        logger.bind(step=2).info("trace_nested_step")
        await sleep(0.05)

    return {"message": "Created 2 nested spans — check Tempo for the trace hierarchy"}


async def _run_background_work(ctx: object) -> None:
    """Background work executed after the response is sent, with propagated trace context."""
    token = otel_context.attach(ctx)  # type: ignore[arg-type]
    try:
        with _tracer.start_as_current_span("background-work"):
            logger.info("background_task_started")
            await sleep(0.2)
            logger.info("background_task_completed")
    finally:
        otel_context.detach(token)


@router.get("/background-task", summary="Background Task Trace Propagation")
async def background_task_endpoint(background_tasks: BackgroundTasks) -> dict[str, str]:
    """Endpoint that enqueues a background task to verify that OpenTelemetry trace context is correctly propagated to background work executed after the response is sent."""
    # Always capture the current context at the time of the request and pass it to the background task.
    # This ensures that even if the background task runs after the request scope has ended, it still has access to the trace context for proper correlation in Tempo.
    ctx = otel_context.get_current()
    background_tasks.add_task(_run_background_work, ctx)
    logger.info("background_task_enqueued")
    return {
        "message": "Response sent — background task running with propagated trace context (verify in Tempo)"
    }
