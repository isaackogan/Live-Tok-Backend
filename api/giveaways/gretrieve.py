from __future__ import annotations

import json
from typing import Optional

import aioredis

from livestuff.live import LiveConnectionPool
from models.response import AsyncResponse


class RetrieveGiveawayResponse(AsyncResponse):

    def __init__(self, username: str, live: LiveConnectionPool, redis: aioredis.Redis):
        super().__init__()
        self.username: str = username
        self.redis: aioredis = redis
        self.live: LiveConnectionPool = live

    async def complete(self) -> RetrieveGiveawayResponse:
        giveaway: Optional[dict] = self.live.giveaways.get_giveaway(self.username)

        # Check if already running
        if giveaway is None:

            res: Optional[bytes] = await self.redis.get(f"gresults:{self.username}")

            if res is None:
                self._status, self._payload = 404, None
            else:
                self._status, self._payload = 200, json.loads(res.decode("utf-8"))

            return self

        self._status, self._payload = 200, giveaway
        return self

