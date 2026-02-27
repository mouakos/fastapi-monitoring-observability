"""Error simulation endpoints for testing error handling and monitoring."""

from asyncio import sleep

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/error", tags=["Errors"])


@router.get(
    "/400",
    summary="Bad Request Error",
    description="Triggers a 400 Bad Request error for testing error handling.",
)
def bad_request() -> None:
    """Simulates a bad request error."""
    raise HTTPException(status_code=400, detail="Bad request example")


@router.get(
    "/401",
    summary="Unauthorized Error",
    description="Triggers a 401 Unauthorized error for testing authentication failures.",
)
def unauthorized() -> None:
    """Simulates an unauthorized access error."""
    raise HTTPException(status_code=401, detail="Unauthorized example")


@router.get(
    "/404",
    summary="Not Found Error",
    description="Triggers a 404 Not Found error for testing missing resource handling.",
)
def not_found() -> None:
    """Simulates a resource not found error."""
    raise HTTPException(status_code=404, detail="Resource not found")


class Item(BaseModel):
    """Model for item validation testing."""

    name: str
    price: float


@router.post(
    "/validation",
    summary="Validation Error",
    description="Triggers a 422 Unprocessable Entity error by sending invalid data.",
)
def validation_error(item: Item) -> Item:
    """Endpoint to test request validation errors."""
    return item


@router.get(
    "/500-controlled",
    summary="Controlled Server Error",
    description="Triggers a controlled 500 Internal Server Error for testing error responses.",
)
def controlled_500() -> None:
    """Simulates a controlled server error."""
    raise HTTPException(status_code=500, detail="Controlled server error")


@router.get(
    "/500-crash",
    summary="Unhandled Exception",
    description="Triggers an unhandled division by zero error to simulate application crashes.",
)
def crash() -> float:
    """Simulates an unhandled exception causing a crash."""
    return 1 / 0


@router.get(
    "/timeout",
    summary="Timeout Simulation",
    description="Simulates a slow endpoint that takes 10 seconds to respond.",
)
async def timeout() -> dict[str, str]:
    """Simulates a slow request that might timeout."""
    await sleep(10)
    return {"message": "Finished after delay"}


@router.get(
    "/external",
    summary="External Service Failure",
    description="Simulates an external service failure with a RuntimeError.",
)
def external_failure() -> None:
    """Simulates an external service dependency failure."""
    raise RuntimeError("External service failed")
