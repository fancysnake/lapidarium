from __future__ import annotations

from typing import TYPE_CHECKING, override

from django.core.cache import cache

from lapidarium.pacts.outreach import ThrottleProtocol

if TYPE_CHECKING:
    import datetime as dt


class CacheThrottle(ThrottleProtocol):
    """A fixed window per key in the default cache, opened by the first attempt."""

    @override
    def allow(self, key: str, *, limit: int, window: dt.timedelta) -> bool:
        cache_key = f"throttle:{key}"
        timeout = window.total_seconds()
        cache.add(cache_key, 0, timeout=timeout)
        try:
            count: int = cache.incr(cache_key)
        except ValueError:
            # The window closed between `add` and `incr`; this attempt opens the next.
            cache.set(cache_key, 1, timeout=timeout)
            count = 1
        return count <= limit
