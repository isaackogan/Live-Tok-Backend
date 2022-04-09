from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import aioredis

from livestuff.live import LiveConnectionPool
from models.payload import GiveawayConfig
from models.response import AsyncResponse


class CreateGiveawayResponse(AsyncResponse):

    def __init__(self, authorization: str, data: GiveawayConfig, live: LiveConnectionPool, redis: aioredis.Redis):
        super().__init__()
        self.data: GiveawayConfig = data
        self.redis: aioredis.Redis = redis
        self.authorization: str = authorization
        self.live: LiveConnectionPool = live

    async def complete(self) -> CreateGiveawayResponse:
        username: Optional[bytes] = await self.redis.get(f"auth:{self.authorization}")

        # Get from Redis
        if username is None:
            self._status, self._payload, self._message = 400, None, "Auth failed"
            return self

        username: str = username.decode("utf-8")
        giveaway: Optional[dict] = self.live.giveaways.get_giveaway(username)

        # Check if tracking rn
        tracking = bool(self.live.clients.get(username))
        if not tracking:
            self._status, self._payload, self._message = 404, None, "Not currently tracking that user"
            return self

        # Check if already running, if so, cancel
        if giveaway is not None:
            self._status, self._payload, self._message = 401, None, "Giveaway is already running"
            return self

        name: str = self.data.prize_name[:20]
        join_word: str = self.data.keyword[:20].replace(" ", "")
        winner_count: int = max(1, min(self.data.winners, 5))
        duration: int = max(1, min(self.data.duration, 60))

        current_time: int = round(datetime.now(timezone.utc).timestamp())
        end_time: int = current_time + (duration * 60)
        giveaway_config: dict = {
            "name": name,
            "join_word": join_word,
            "winner_count": winner_count,
            "start_time": current_time,
            "end_time": end_time
        }

        self.live.giveaways.set_giveaway(username, giveaway_config)
        self._status, self._payload, self._message = 200, giveaway_config, "Started giveaway"
        return self

