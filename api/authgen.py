from __future__ import annotations

import random
from typing import Optional

import aioredis
from models.response import AsyncResponse


class GenerateAuthToken(AsyncResponse):

    def __init__(self, client_id: str, redis: aioredis.Redis):
        super().__init__()

        self.client_id: str = client_id
        self.redis: aioredis = redis

    async def complete(self) -> GenerateAuthToken:
        auth: Optional[bytes] = await self.redis.get(f"genauth:{self.client_id}")

        # Get from Redis
        if auth is not None:
            auth: str = auth.decode("utf-8")

        # Get a new code
        else:
            auth: str = str(random.randint(100000, 999999))
            await self.redis.set(f"genauth:{self.client_id}", auth, ex=3600)

        self._status, self._payload = 200, auth
        return self

