import time
from collections import defaultdict
from typing import Optional

from fastapi import Request

from app.core.errors import RateLimitedError


class InMemoryRateLimiter:
    def __init__(self, requests_per_minute: int = 60, window_seconds: float = 60.0):
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self.history: dict[str, list[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP from comma-separated list
            return forwarded_for.split(",")[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return "127.0.0.1"

    async def __call__(self, request: Request) -> None:
        ip = self._get_client_ip(request)
        now = time.monotonic()
        cutoff = now - self.window_seconds

        # Prune old timestamps
        timestamps = [t for t in self.history[ip] if t > cutoff]
        self.history[ip] = timestamps

        if len(timestamps) >= self.requests_per_minute:
            raise RateLimitedError(
                message=f"Rate limit exceeded: {self.requests_per_minute} requests per minute",
                details={
                    "limit": self.requests_per_minute,
                    "window_seconds": self.window_seconds,
                    "retry_after": max(1, int(cutoff - timestamps[0])) if timestamps else 1,
                },
            )

        self.history[ip].append(now)

    def reset(self, ip: Optional[str] = None) -> None:
        if ip:
            self.history.pop(ip, None)
        else:
            self.history.clear()


# Default dependency for endpoints: 60 requests per minute
rate_limit = InMemoryRateLimiter(requests_per_minute=60)
