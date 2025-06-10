import asyncio
import time

class RateLimiter:
    def __init__(self, rate_per_sec: float = 1.0):
        self.rate_per_sec = rate_per_sec
        self.min_interval = 1.0 / rate_per_sec
        self.lock = asyncio.Lock()
        self.last_call = 0.0

    async def acquire(self):
        async with self.lock:
            now = time.monotonic()
            wait_time = self.min_interval - (now - self.last_call)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self.last_call = time.monotonic() 