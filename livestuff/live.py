import asyncio
import logging
import random
import traceback
from typing import List, Dict

import aiomysql
import aioredis
from TikTokLive import TikTokLiveClient
from TikTokLive.types import FailedConnection
from TikTokLive.types.events import CommentEvent, GiftEvent

import config
from livestuff.giveaway import LiveGiveaways
from utilities.statistics_sql import StatisticSQL


class LiveConnectionPool:

    def __init__(self, sql_pool: aiomysql.Pool, redis: aioredis.Redis):
        self.sql_pool: aiomysql.Pool = sql_pool
        self.redis: aioredis.Redis = redis
        self.clients: Dict[str, TikTokLiveClient] = dict()
        self.giveaways: LiveGiveaways = LiveGiveaways(asyncio.get_running_loop(), self.redis)

    async def remove_client(self, username: str) -> bool:
        c = self.clients.get(username)

        try:
            del self.clients[username]
        except KeyError:
            pass

        try:
            await c.stop()
        except:
            pass

        self.giveaways.del_giveaway(username)
        return True

    async def add_client(self, username: str) -> bool:
        client: TikTokLiveClient = TikTokLiveClient(unique_id=username, **{"process_initial_data": False, "enable_extended_gift_info": True})

        @client.on("comment")
        async def _on_message(event: CommentEvent):
            sql: StatisticSQL = StatisticSQL(self.sql_pool)
            add_xp: int = random.randint(config.Leaderboard.MAX_ADD_CHAT_XP, config.Leaderboard.MAX_ADD_CHAT_XP)
            await self.redis.set(f"avatar:{event.user.uniqueId}", event.user.profilePicture.avatar_url, ex=14400)
            await sql.update_statistics(event.user.uniqueId, client.unique_id, 1, add_xp, 0)
            self.giveaways.handle_comment(event, client.unique_id)

        @client.on("gift")
        async def _on_gift(event: GiftEvent):
            coins = 0

            # If it's type 1 and the streak is over
            if event.gift.gift_type == 1 and event.gift.repeat_end == 1:
                coins = event.gift.repeat_count * event.gift.extended_gift.diamond_count * 2

            # It's not type 1, which means it can't have a streak & is automatically over
            elif event.gift.gift_type != 1:
                coins = event.gift.extended_gift.diamond_count * 2

            # Number of sent coins
            if coins < 1:
                return

            # Add Statistics
            xp_per_coin: int = random.randint(config.Leaderboard.MIN_ADD_PER_COIN_XP, config.Leaderboard.MAX_ADD_PER_COIN_XP)
            add_xp: int = xp_per_coin * coins
            sql: StatisticSQL = StatisticSQL(self.sql_pool)
            await sql.update_statistics(event.user.uniqueId, client.unique_id, 0, add_xp, coins)
            await self.redis.set(f"avatar:{event.user.uniqueId}", event.user.profilePicture.avatar_url, ex=14400)

        # Add the client
        try:
            await client.start()
            self.clients[username] = client
            return True
        except:
            return False
