from __future__ import annotations

import asyncio
import json
import logging
import traceback
from concurrent.futures import ProcessPoolExecutor
from json import JSONDecodeError

import aiohttp
import aioredis
from TikTokApi import TikTokApi

from typing import Tuple, Optional, Dict, Union
from models.response import AsyncResponse


class TikTokProfileLiveResponse(AsyncResponse):
    TIKTOK_API = TikTokApi()
    DEFAULT_CLIENT_PARAMS: Dict[str, Union[int, bool, str]] = {
        "aid": 1988, "app_language": 'en-US', "app_name": 'tiktok_web', "browser_language": 'en', "browser_name": 'Mozilla',
        "browser_online": True, "browser_platform": 'Win32', "version_code": 180800,
        "browser_version": '5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36',
        "cookie_enabled": True, "cursor": '', "device_platform": 'web', "did_rule": 3, "fetch_rule": 1, "identity": 'audience', "internal_ext": '',
        "last_rtt": 0, "live_id": 12, "resp_content_type": 'protobuf', "screen_height": 1152, "screen_width": 2048, "tz_name": 'Europe/Berlin',
    }

    DEFAULT_REQUEST_HEADERS: Dict[str, str] = {
        "Connection": 'keep-alive', "Cache-Control": 'max-age=0', "Accept": 'text/html,application/json,application/protobuf',
        "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36',
        "Referer": 'https://www.tiktok.com/', "Origin": 'https://www.tiktok.com', "Accept-Language": 'en-US,en;q=0.9', "Accept-Encoding": 'gzip, deflate',
    }

    def __init__(self, username: str):
        super().__init__()
        self.unique_id: str = username

    TIKTOK_URL_WEB: str = 'https://www.tiktok.com/'
    TIKTOK_LIVE_URL: str = f"https://m.tiktok.com/node/share/live"

    async def get_livestream_page_html(self, unique_id: str) -> str:
        request_url: str = f"{self.TIKTOK_URL_WEB}@{unique_id}/live"
        async with aiohttp.ClientSession() as session:
            async with session.get(request_url, headers=self.DEFAULT_REQUEST_HEADERS, timeout=10000) as request:
                return (await request.read()).decode(encoding="utf-8")

    async def get_node_data(self, room_id: str) -> dict:
        request_url: str = self.TIKTOK_LIVE_URL + f"?id={room_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(request_url, headers=self.DEFAULT_REQUEST_HEADERS, timeout=10000) as request:
                return await request.json()

    @staticmethod
    def get_room_id(html: str) -> Optional[str]:
        try:
            return html.split("__room_id=")[1].split("\"/>")[0]
        except:
            pass

        try:
            return html.split('"roomId":"')[1].split('"}')[0]
        except:
            pass

        return None

    async def __fetch_room_id(self) -> Optional[str]:
        try:
            html: str = await self.get_livestream_page_html(self.unique_id)
            self.__room_id = self.get_room_id(html)
            return self.__room_id
        except:
            return None

    async def __fetch_room_data(self, room_id: str) -> Optional[dict]:
        try:
            return await self.get_node_data(room_id)
        except:
            return None

    async def complete(self) -> TikTokProfileLiveResponse:
        room_id: Optional[str] = await self.__fetch_room_id()

        if room_id:
            room_data: dict = await self.__fetch_room_data(room_id)
            if room_data and room_data.get("body", dict()).get("status") == '2':
                self._status, self._payload = 200, room_id
                return self

        self._status, self._payload = 404, None
        return self
