import asyncio
import os
from asyncio import AbstractEventLoop
from typing import Mapping, List, Optional

import aiomysql as aiomysql
import aioredis as aioredis
import uvicorn
from fastapi import Depends, FastAPI
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware

import config
from api.authgen.authgen import GenerateAuthToken
from api.authgen.authgencheck import CheckAuthGenToken
from api.creator import TikTokCreatorResponse
from api.getdashboard import GetDashboardData
from api.giveaways.gcreate import CreateGiveawayResponse
from api.giveaways.gdelete import DeleteGiveawayResponse
from api.giveaways.gretrieve import RetrieveGiveawayResponse
from api.giveaways.gupdate import UpdateGiveawayResponse
from api.live import TikTokProfileLiveResponse
from api.mantrack import ManageTrackingResponse
from api.profile import TikTokProfileResponse
from livestuff.live import LiveConnectionPool
from models.mysql import create_template
from models.payload import GiveawayConfig
from models.response import FilledResponse

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"


class LiveTokAPI(FastAPI):

    @classmethod
    def __configuration(cls, **extra: Mapping):
        new: Mapping = {
            "docs_url": '/',
            "redoc_url": "/docs",
            "description": "Backend API for the LiveTok TikTok Service",
            "title": "LiveTok Backend",
            "version": "0.6.9",
            "openapi_url": "/api-docs",
        }
        extra.update(new)
        return extra

    def __init__(self, redis_host: str, redis_port: int, redis_password: str, **extra: dict):
        super().__init__(**self.__configuration(**extra))
        self.redis: Optional[aioredis.Redis] = None
        self.redis_host: str = redis_host
        self.redis_port: int = redis_port
        self.redis_password: str = redis_password
        self.origins: List[str] = ["*"]
        self.add_middleware(
            CORSMiddleware,
            allow_origins=self.origins,
            allow_methods=self.origins,
            allow_headers=self.origins,
            allow_credentials=True
        )

        try:
            self.loop: AbstractEventLoop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop: AbstractEventLoop = asyncio.get_event_loop()

        self.sql_pool: Optional[aiomysql.Pool] = None
        self.live: Optional[LiveConnectionPool] = None


app: LiveTokAPI = LiveTokAPI(
    config.Redis.HOST,
    config.Redis.PORT,
    config.Redis.PASSWORD
)


@app.on_event("startup")
async def startup():
    print("Go for launch!")

    app.sql_pool = await aiomysql.create_pool(
        host=config.MariaDB.HOST, port=config.MariaDB.PORT,
        user=config.MariaDB.USERNAME, password=config.MariaDB.PASSWORD,
        db=config.MariaDB.DATABASE, loop=app.loop
    )

    await create_template(app.sql_pool, file_path=config.MariaDB.SQL_TEMPLATE_PATH)
    app.redis = aioredis.Redis(host=app.redis_host, port=app.redis_port, password=app.redis_password)
    app.live = LiveConnectionPool(app.sql_pool, app.redis)
    await FastAPILimiter.init(app.redis)


@app.put("/creator/dashboard/giveaway", tags=['Giveaway'])
async def create_giveaway(authorization: str, giveaway_config: GiveawayConfig):
    return (await CreateGiveawayResponse(authorization=authorization, data=giveaway_config, redis=app.redis, live=app.live).complete()).serialize()


@app.patch("/creator/dashboard/giveaway", tags=['Giveaway'])
async def update_giveaway(authorization: str, giveaway_config: GiveawayConfig):
    return (await UpdateGiveawayResponse(authorization=authorization, data=giveaway_config, redis=app.redis, live=app.live).complete()).serialize()


@app.delete("/creator/dashboard/giveaway", tags=['Giveaway'])
async def delete_giveaway(authorization: str, pick_winner: bool):
    return (await DeleteGiveawayResponse(authorization=authorization, pick_winner=pick_winner, redis=app.redis, live=app.live).complete()).serialize()


@app.get("/creator/giveaway", tags=['Giveaway'])
async def get_giveaway(username: str):
    return (await RetrieveGiveawayResponse(username=username, redis=app.redis, live=app.live).complete()).serialize()


@app.get("/creator/auth/generate", tags=['Authentication'])
async def gen_auth_code(client_id: str):
    return (await GenerateAuthToken(client_id=client_id, redis=app.redis).complete()).serialize()


@app.post("/creator/auth/check", tags=['Authentication'])
async def check_auth_code(client_id: str, username: str):
    return (await CheckAuthGenToken(username=username, client_id=client_id, redis=app.redis).complete()).serialize()


@app.get("/creator/dashboard", tags=['Dashboard'])
async def get_dashboard_data(authorization: str):
    return (await GetDashboardData(authorization=authorization, redis=app.redis, live=app.live).complete()).serialize()


@app.post("/creator/dashboard/start", tags=['Dashboard'])
async def start_tracking_data(authorization: str):
    return (await ManageTrackingResponse(authorization=authorization, redis=app.redis, live=app.live, start_or_stop=True).complete()).serialize()


@app.post("/creator/dashboard/stop", tags=['Dashboard'])
async def stop_tracking_data(authorization: str):
    return (await ManageTrackingResponse(authorization=authorization, redis=app.redis, live=app.live, start_or_stop=False).complete()).serialize()


@app.get("/tiktok/user", tags=['User'], dependencies=[Depends(RateLimiter(times=50, seconds=10))])
async def get_tiktok_user(username: str, use_cache: bool = True):
    return (await TikTokProfileResponse(username=username, redis=app.redis, use_cache=use_cache).complete()).serialize()


@app.get("/tiktok/user/live", tags=['User'], dependencies=[Depends(RateLimiter(times=50, seconds=10))])
async def get_tiktok_user_live(username: str):
    return (await TikTokProfileLiveResponse(username=username).complete()).serialize()


@app.get("/creator/statistics", tags=['User'])
async def get_creator_statistics(username: str):
    return (await TikTokCreatorResponse(username=username, sql_pool=app.sql_pool, redis=app.redis).complete()).serialize()


@app.get("/tiktok/user/page-data", tags=['User'], dependencies=[Depends(RateLimiter(times=50, seconds=10))])
async def get_tiktok_user_page_data(username: str):
    live_data: TikTokProfileLiveResponse = await TikTokProfileLiveResponse(username=username).complete()

    # Live doesn't exist
    if live_data.status == 404:
        return FilledResponse(status=404, payload=None).serialize()

    # Live does exist, get user data
    user_data: TikTokProfileResponse = await TikTokProfileResponse(username=username, redis=app.redis, use_cache=True).complete()
    payload: dict = user_data.payload
    payload["roomId"] = live_data.payload

    # Get Leaderboard Data
    leaderboard_data = await TikTokCreatorResponse(username=username, sql_pool=app.sql_pool, redis=app.redis).complete()
    payload["leaderboards"] = leaderboard_data.payload

    # Get Giveaway Data
    giveaway_data = (await RetrieveGiveawayResponse(username, app.live, app.redis).complete())
    payload["giveaway"] = giveaway_data.payload

    return FilledResponse(status=user_data.status, payload=payload).serialize()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT, log_level="info", proxy_headers=True)
