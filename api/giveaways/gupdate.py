from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

import aioredis

from livestuff.live import LiveConnectionPool
from models.payload import GiveawayConfig
from models.response import AsyncResponse


class UpdateGiveawayResponse(AsyncResponse):

    def __init__(self, authorization: str, data: GiveawayConfig, live: LiveConnectionPool, redis: aioredis.Redis):
        super().__init__()
        self.data: GiveawayConfig = data
        self.authorization: str = authorization
        self.redis: aioredis = redis
        self.live: LiveConnectionPool = live

    async def complete(self) -> UpdateGiveawayResponse:
        username: Optional[bytes] = await self.redis.get(f"auth:{self.authorization}")

        # Get from Redis
        if username is None:
            self._status, self._payload, self._message = 400, None, "Authentcation Failed"
            return self

        username: str = username.decode("utf-8")
        giveaway: Optional[dict] = self.live.giveaways.get_giveaway(username)

        # Check if running
        if giveaway is None:
            self._status, self._payload = 404, None
            return self

        name: str = self.data.prize_name[:20]
        join_word: str = self.data.keyword[:20].replace(" ", "")
        winner_count: int = max(1, min(self.data.winners, 5))

        # TODO Prevent editing end time once started in React Site
        giveaway_config: dict = {
            "name": name,
            "join_word": join_word,
            "winner_count": winner_count,
            "start_time": giveaway["start_time"],
            "end_time": giveaway["end_time"]
        }

        self.live.giveaways.set_giveaway(username, giveaway_config)
        self._status, self._payload = 200, giveaway_config
        return self

