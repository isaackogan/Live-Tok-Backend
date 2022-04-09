from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

import aioredis

import config
from livestuff.live import LiveConnectionPool
from models.payload import GiveawayConfig
from models.response import AsyncResponse


class DeleteGiveawayResponse(AsyncResponse):

    def __init__(self, authorization: str, pick_winner: bool, redis: aioredis.Redis, live: LiveConnectionPool):
        super().__init__()
        self.pick_winner: bool = pick_winner
        self.authorization: str = authorization
        self.redis: aioredis = redis
        self.live: LiveConnectionPool = live

    async def complete(self) -> DeleteGiveawayResponse:
        username: Optional[bytes] = await self.redis.get(f"auth:{self.authorization}")

        # Get from Redis
        if username is None:
            self._status, self._payload, self._message = 400, None, "Authentication failed"
            return self

        username: str = username.decode("utf-8")
        giveaway: Optional[dict] = self.live.giveaways.get_giveaway(username)

        # Check if running
        if giveaway is None:
            self._status, self._payload, self._message = 404, None, "Giveaway not found"
            return self

        current_time: int = round(datetime.now(timezone.utc).timestamp())
        giveaway["ended_at"] = current_time

        if self.pick_winner:
            winner_count: int = giveaway["winner_count"]
            giveaway["winners"] = self.live.giveaways.pick_winners(username, winner_count)
            await self.redis.set(f"gresults:{username}", json.dumps(giveaway), ex=config.GIVEAWAY_FINISH_EXPIREY)
        else:
            giveaway["winners"] = None

        self.live.giveaways.del_giveaway(username)
        # TODO remember to delete data on natural end too

        self._status, self._payload = 200, giveaway
        return self

