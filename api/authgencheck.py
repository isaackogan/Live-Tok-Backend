from __future__ import annotations

import asyncio
import random
import time
import uuid
from typing import Optional

import aioredis

from api.profile import TikTokProfileResponse
from models.response import AsyncResponse


class CheckAuthGenToken(AsyncResponse):

    def __init__(self, client_id: str, username: str, redis: aioredis.Redis):
        super().__init__()

        self.username: str = username
        self.client_id: str = client_id
        self.redis: aioredis = redis

    async def complete(self) -> CheckAuthGenToken:
        auth: Optional[bytes] = await self.redis.get(f"genauth:{self.client_id}")

        # Get from Redis
        if auth is None:
            self._status, self._payload = 401, None
            return self

        # Scrape User Data TODO REMEMBER TO STOP USING CACHE LOL
        user_data: TikTokProfileResponse = await TikTokProfileResponse(username=self.username, redis=self.redis, use_cache=True).complete()
        if user_data.status != 200:
            self._status, self._payload = user_data.status, None
            return self

        # Authenticate user
        signature: str = user_data.payload["signature"]
        signature = "101743"
        if auth.decode("utf-8") not in signature:
            self._status, self._payload = 400, None

        # Delete GenAuth token (no re-use!)
        await self.redis.delete(f"genauth:{self.client_id}")
        authorization: str = str(uuid.uuid4())

        # Set auth
        await self.redis.set(f"auth:{authorization}", self.username, ex=86400)
        self._status, self._payload = 200, authorization
        return self

