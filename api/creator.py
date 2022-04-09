from __future__ import annotations

import math
import random
from typing import List

import aiomysql
import aioredis

import config
from models.response import AsyncResponse
from utilities.statistics_sql import StatisticSQL


class TikTokCreatorResponse(AsyncResponse):

    def __init__(self, username: str, sql_pool: aiomysql.Pool, redis: aioredis.Redis):
        super().__init__()
        self.username: str = username
        self.redis: aioredis.Redis = redis
        self.sql_pool: aiomysql.Pool = sql_pool

    @classmethod
    def calculate_level(cls, xp: int):
        return abs(
            math.floor((math.sqrt(10) / 10) * math.sqrt(xp))
        )

    @classmethod
    def calculate_xp(cls, level: int):
        return abs(
            10 * (math.floor(level) ** 2)
        )

    async def complete(self) -> TikTokCreatorResponse:
        sql: StatisticSQL = StatisticSQL(self.sql_pool)
        items: List[dict] = []

        # (viewer_id, comments, experience, coins)
        statistics = await sql.get_statistics(self.username)

        for stat in statistics:
            xp = stat[2]
            level: int = self.calculate_level(stat[2])
            current_xp: int = xp - self.calculate_xp(level)
            needed_xp: int = self.calculate_xp(level + 1) - self.calculate_xp(level)

            avatar_url = await self.redis.get(f"avatar:{stat[0]}")
            avatar_url = avatar_url.decode("utf-8") if avatar_url is not None else None

            items.append({
                "avatar_url": avatar_url,
                "unique_id": stat[0],
                "messages": stat[1],
                "coins": stat[3],
                "experience": stat[2],
                "current_xp": current_xp,
                "required_xp": needed_xp,
                "level": level
            })

        self._status, self._payload = 200, items
        return self
