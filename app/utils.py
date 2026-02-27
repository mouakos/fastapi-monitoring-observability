"""Shared utilities for extracting structured request information."""

from dataclasses import dataclass

from starlette.requests import Request


@dataclass(frozen=True, slots=True)
class RequestInfo:
    """Immutable snapshot of relevant HTTP request fields."""

    method: str
    path: str
    route_path: str
    client_ip: str
    user_agent: str | None


def get_request_info(request: Request) -> RequestInfo:
    """Extract structured request information from a Starlette Request.

    Args:
        request: The incoming HTTP request.

    Returns:
        A :class:`RequestInfo` instance populated from the request.
    """
    route = request.scope.get("route")
    return RequestInfo(
        method=request.method,
        path=request.url.path,
        route_path=route.path if route else request.url.path,
        client_ip=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent"),
    )
