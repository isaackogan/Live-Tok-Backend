from __future__ import annotations

import random
from typing import Optional

import aioredis

from live.live import LiveConnectionPool
from models.response import AsyncResponse


class ManageTrackingResponse(AsyncResponse):

    def __init__(self, authorization: str, redis: aioredis.Redis, live: LiveConnectionPool, start_or_stop: bool):
        super().__init__()
        self.authorization: str = authorization
        self.redis: aioredis = redis
        self.live: LiveConnectionPool = live
        self.start_or_stop: bool = start_or_stop

    async def complete(self) -> ManageTrackingResponse:
        username: Optional[bytes] = await self.redis.get(f"auth:{self.authorization}")

        # Get from Redis
        if username is None:
            self._status, self._payload = 404, None
            return self

        username: str = username.decode("utf-8")
        c = self.live.clients.get(username)

        # Stop Stream
        if not self.start_or_stop:
            if c:
                try:
                    del self.live.clients[username]
                except KeyError:
                    pass
                await c.stop()

            self._status, self._payload = 200, True
            return self

        # Already Connected
        if c:
            self._status, self._payload = 400, False
            return self

        success: bool = await self.live.add_client(username)
        self._status, self._payload = 200 if success else 500, success
        return self
