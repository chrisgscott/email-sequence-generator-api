from functools import wraps
import time
import asyncio

class RateLimiter:
    def __init__(self, calls_per_minute):
        self.calls_per_minute = calls_per_minute
        self.interval = 60 / calls_per_minute
        self.last_call = 0

    async def wait(self):
        now = time.time()
        elapsed = now - self.last_call
        if elapsed < self.interval:
            await asyncio.sleep(self.interval - elapsed)
        self.last_call = time.time()

def rate_limit(calls_per_minute):
    limiter = RateLimiter(calls_per_minute)
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            await limiter.wait()
            return await func(*args, **kwargs)
        return wrapper
    return decorator

openai_limiter = rate_limit(60)  # Adjust the rate limit as needed