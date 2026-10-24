"""Small 100-request concurrency check for an available platform endpoint.

Example: python performance_check.py http://127.0.0.1:8000/health
For authenticated routes, pass --token TOKEN. This is a smoke measurement, not a
replacement for a representative database-backed load test.
"""

import argparse
import asyncio
import sys
import time

import httpx


async def measure(url: str, token: str | None, concurrency: int) -> tuple[list[float], int]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(headers=headers, limits=limits, timeout=httpx.Timeout(10.0)) as client:
        async def request() -> tuple[float, bool]:
            start = time.perf_counter()
            try:
                response = await client.get(url)
                return time.perf_counter() - start, response.is_success
            except httpx.HTTPError:
                return time.perf_counter() - start, False

        results = await asyncio.gather(*(request() for _ in range(concurrency)))
    return [elapsed for elapsed, _ in results], sum(1 for _, ok in results if ok)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--token")
    parser.add_argument("--concurrency", type=int, default=100)
    args = parser.parse_args()
    if args.concurrency < 1:
        parser.error("--concurrency must be positive")
    durations, successes = asyncio.run(measure(args.url, args.token, args.concurrency))
    ordered = sorted(durations)
    p95 = ordered[max(0, int(0.95 * len(ordered)) - 1)]
    print(f"requests={len(durations)} successful={successes} p95_seconds={p95:.3f} max_seconds={max(durations):.3f}")
    return 0 if successes == len(durations) and p95 <= 2.0 else 1


if __name__ == "__main__":
    sys.exit(main())
