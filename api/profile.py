from __future__ import annotations

import asyncio
import json
import logging
import traceback
from concurrent.futures import ProcessPoolExecutor
from json import JSONDecodeError

import aioredis
from TikTokApi import TikTokApi

import functools
from typing import Tuple, Optional

from TikTokApi.api.user import User

import config
from models.response import AsyncResponse


class TikTokProfileResponse(AsyncResponse):
    TIKTOK_API = TikTokApi()

    def __init__(self, username: str, redis: aioredis.Redis, use_cache: bool = True):
        super().__init__()

        self.unique_id: str = username
        self.redis: aioredis = redis
        self.use_cache: bool = use_cache

    @staticmethod
    def _request(username: str) -> Tuple[int, Optional[TikTokApi.user]]:
        """
        Make a request to the TikTok API

        """
        try:
            return 200, TikTokProfileResponse.TIKTOK_API.user(username)
        except:
            logging.error(traceback.format_exc())
            return 500, None

    async def complete(self) -> TikTokProfileResponse:

        user: Optional[bytes] = await self.redis.get(f"user:{self.unique_id}")

        # Get from Redis
        if user is not None and self.use_cache:
            user: str = user.decode("utf-8")

            try:
                code, payload = 200, json.loads(user)

            except JSONDecodeError:

                # Reference (DNE or Different Key)
                if 'ref' == user[:3]:
                    reference: str = user.split(":")[2]

                    # User DNE
                    if reference == "-1":
                        code, payload = 404, None

                    # Get Reference
                    else:
                        user: str = (await self.redis.get(f"user:{reference}")).decode("utf-8")
                        code, payload = 200, json.loads(user)

                else:

                    # Broken Redis String
                    code, payload = 500, None

        else:

            code, user = await asyncio.get_running_loop().run_in_executor(
                ProcessPoolExecutor(),
                functools.partial(self._request, username=self.unique_id)
            )

            # noinspection PyTypeChecker
            user: User = user

            if code == 404:
                payload = None
                await self.redis.set(f"user:{self.unique_id}", "ref:user:-1", ex=config.TikTokScraping.EXPIRE_SCRAPED_USERS)

            elif code == 200:
                payload = user.as_dict

                # Cache data and also references for the alternative ID types
                await self.redis.set(f"user:{user.user_id}", json.dumps(payload), ex=config.TikTokScraping.EXPIRE_SCRAPED_USERS)
                await self.redis.set(f"user:{user.sec_uid}", f"ref:user:{user.user_id}", ex=config.TikTokScraping.EXPIRE_SCRAPED_USERS)
                await self.redis.set(f"user:{user.username}", f"ref:user:{user.user_id}", ex=config.TikTokScraping.EXPIRE_SCRAPED_USERS)

            else:
                payload = None

        self._status, self._payload = code, payload
        return self
