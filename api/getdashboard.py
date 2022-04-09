from __future__ import annotations

import random
from typing import Optional

import aioredis

from api.giveaways.gretrieve import RetrieveGiveawayResponse
from livestuff.live import LiveConnectionPool
from models.response import AsyncResponse


class GetDashboardData(AsyncResponse):

    def __init__(self, authorization: str, redis: aioredis.Redis, live: LiveConnectionPool):
        super().__init__()
        self.authorization: str = authorization
        self.redis: aioredis = redis
        self.live: LiveConnectionPool = live

    async def complete(self) -> GetDashboardData:
        username: Optional[bytes] = await self.redis.get(f"auth:{self.authorization}")

        # Get from Redis
        if username is None:
            self._status, self._payload = 404, None
            return self

        username: str = username.decode("utf-8")
        giveaway: RetrieveGiveawayResponse = await RetrieveGiveawayResponse(username=username, live=self.live, redis=self.redis).complete()

        data = {
            "unique_id": username,
            "tracking": bool(self.live.clients.get(username)),
            "giveaway": giveaway.payload
        }

        self._status, self._payload = 200, data
        return self

