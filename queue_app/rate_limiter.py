"""
Sliding-window rate limiter (Redis sorted set + Lua EVAL for atomicity).
See DESIGN.md and ANSWERS.md for full trade-off analysis.
"""
import time, uuid
import redis
from django.conf import settings

_redis_client = None

def get_redis_client():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(settings.REDIS_URL)
    return _redis_client

_SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]
redis.call('ZREMRANGEBYSCORE', key, 0, now - window_ms)
local count = redis.call('ZCARD', key)
if count < limit then
    redis.call('ZADD', key, now, member)
    redis.call('PEXPIRE', key, window_ms)
    return 1
else
    return 0
end
"""

class SlidingWindowRateLimiter:
    """Fails CLOSED on Redis errors -- see ANSWERS.md for justification."""
    def __init__(self, key, limit=200, window_seconds=60, client=None):
        self.key = key
        self.limit = limit
        self.window_ms = window_seconds * 1000
        self.client = client or get_redis_client()

    def allow(self):
        now_ms = int(time.time() * 1000)
        member = f"{now_ms}-{uuid.uuid4().hex[:8]}"
        result = self.client.eval(_SLIDING_WINDOW_LUA, 1, self.key, now_ms, self.window_ms, self.limit, member)
        return bool(result)
