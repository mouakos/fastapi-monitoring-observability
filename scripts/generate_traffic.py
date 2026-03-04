"""Traffic generation script for FastAPI Monitoring & Observability.

Sends a realistic mix of requests across all demo endpoints to populate
Grafana dashboards with metrics, logs, and traces.

Usage:
    uv run python scripts/generate_traffic.py
    uv run python scripts/generate_traffic.py --base-url http://localhost:8000 --rounds 20
    uv run python scripts/generate_traffic.py --duration 60   # run for 60 seconds
"""

import argparse
import asyncio
import sys
import time
from dataclasses import dataclass, field

import httpx

# ---------------------------------------------------------------------------
# Endpoint definitions
# ---------------------------------------------------------------------------


@dataclass
class Endpoint:
    """Definition of an API endpoint to target with generated traffic."""

    method: str
    path: str
    label: str
    weight: int = 1  # relative frequency
    params: dict[str, str] = field(default_factory=dict)
    expect_error: bool = False  # 4xx/5xx is intentional


ENDPOINTS: list[Endpoint] = [
    # High-frequency baseline traffic
    Endpoint("GET", "/", "root", weight=2),
    Endpoint("GET", "/info", "info", weight=2),
    Endpoint("GET", "/random-status", "random-status", weight=10),
    # Latency signals (fast + slow variants)
    Endpoint("GET", "/slow", "slow-0.3s", weight=3, params={"delay": "0.3"}),
    Endpoint("GET", "/slow", "slow-1s", weight=2, params={"delay": "1.0"}),
    Endpoint("GET", "/slow", "slow-2s", weight=1, params={"delay": "2.0"}),
    # Exception / error traces
    Endpoint("GET", "/crash", "crash", weight=1, expect_error=True),
    # Distributed trace scenarios
    Endpoint("GET", "/chain", "chain", weight=2),
    Endpoint("GET", "/trace-nested", "trace-nested", weight=2),
    Endpoint("GET", "/background-task", "background-task", weight=2),
]

# Expand by weight into a flat list for random.choice-style selection
_POOL: list[Endpoint] = [ep for ep in ENDPOINTS for _ in range(ep.weight)]


# ---------------------------------------------------------------------------
# Request runner
# ---------------------------------------------------------------------------


async def send_request(client: httpx.AsyncClient, ep: Endpoint, base_url: str) -> tuple[int, float]:
    """Send a single request and return (status_code, elapsed_ms)."""
    url = f"{base_url}{ep.path}"
    start = time.perf_counter()
    try:
        resp = await client.request(ep.method, url, params=ep.params, timeout=10.0)
        elapsed = (time.perf_counter() - start) * 1000
        return resp.status_code, elapsed
    except httpx.RequestError as exc:
        elapsed = (time.perf_counter() - start) * 1000
        print(f"  [ERROR] {ep.label}: {exc}", file=sys.stderr)
        return 0, elapsed


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


async def run(base_url: str, rounds: int | None, duration: float | None) -> None:
    """Run traffic generation for a fixed number of rounds or a fixed duration."""
    import random

    total_requests = 0
    status_counts: dict[int, int] = {}
    deadline = time.monotonic() + duration if duration else None

    print(f"Target: {base_url}")
    print(f"Mode:   {'duration=' + str(duration) + 's' if deadline else 'rounds=' + str(rounds)}")
    print(f"Pool:   {len(_POOL)} weighted endpoint slots across {len(ENDPOINTS)} endpoints")
    print("-" * 60)

    round_num = 0
    async with httpx.AsyncClient(follow_redirects=True) as client:
        while True:
            if deadline and time.monotonic() >= deadline:
                break
            if rounds is not None and round_num >= rounds:
                break

            round_num += 1
            ep = random.choice(_POOL)
            status, elapsed = await send_request(client, ep, base_url)
            total_requests += 1
            status_counts[status] = status_counts.get(status, 0) + 1

            status_str = str(status) if status else "ERR"
            print(f"  [{round_num:>4}] {ep.label:<20} {status_str}  {elapsed:>7.1f} ms")

            # Small jitter between requests (50–200 ms) to avoid a perfectly
            # uniform load that looks artificial in dashboards
            await asyncio.sleep(random.uniform(0.05, 0.2))

    # Summary
    print("-" * 60)
    print(f"Done — {total_requests} requests sent")
    for code in sorted(status_counts):
        label = "ERR (connection)" if code == 0 else str(code)
        print(f"  {label}: {status_counts[code]}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate realistic traffic against the FastAPI observability demo.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the FastAPI app (default: http://localhost:8000)",
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--rounds",
        type=int,
        default=50,
        help="Number of requests to send (default: 50). Ignored if --duration is set.",
    )
    mode.add_argument(
        "--duration",
        type=float,
        metavar="SECONDS",
        help="Run continuously for this many seconds instead of a fixed round count.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        asyncio.run(
            run(
                base_url=args.base_url,
                rounds=None if args.duration else args.rounds,
                duration=args.duration,
            )
        )
    except KeyboardInterrupt:
        print("\nStopped by user.")
