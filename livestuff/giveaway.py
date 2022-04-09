import asyncio
import json
import random
from asyncio import AbstractEventLoop
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

import aioredis
from TikTokLive.types.events import CommentEvent

import config


class LiveGiveaways:

    def __init__(self, loop: AbstractEventLoop, redis: aioredis.Redis):
        self.redis: aioredis.Redis = redis
        self.__giveaways: Dict[str, dict] = dict()
        self.__entrants: Dict[str, Set[str]] = dict()
        self.loop: AbstractEventLoop = loop
        self.loop.create_task(self.check_loop())

    async def check_loop(self):

        while True:
            current_time: int = round(datetime.now(timezone.utc).timestamp())

            for username, giveaway in self.__giveaways.items():
                self.loop.create_task(self._check_giveaway(username, giveaway, current_time))

            await asyncio.sleep(2)

    async def _check_giveaway(self, username: str, giveaway: dict, current_time: int):

        if current_time > giveaway["end_time"]:
            giveaway["winners"] = self.pick_winners(username, giveaway["winner_count"])
            await self.redis.set(f"gresults:{username}", json.dumps(giveaway), ex=config.GIVEAWAY_FINISH_EXPIREY)
            self.del_giveaway(username)

    def set_giveaway(self, username: str, data: dict):
        self.__giveaways[username] = data
        self.__entrants[username] = set()

    def del_giveaway(self, username: str):
        try:
            del self.__giveaways[username]
        except:
            pass

        try:
            del self.__entrants[username]
        except:
            pass

    def get_giveaway(self, username: str):
        return self.__giveaways.get(username)

    def handle_comment(self, event: CommentEvent, username: str):
        giveaway: Optional[dict] = self.__giveaways.get(username)

        if giveaway and giveaway.get("join_word") in event.comment:
            self.__entrants[username].add(event.user.uniqueId)

    def pick_winners(self, username: str, winners: int) -> List[str]:
        entrants = self.__entrants.get(username, [])
        return random.sample(entrants, min(len(entrants), winners))
