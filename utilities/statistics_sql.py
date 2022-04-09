import datetime
import logging
import traceback
from typing import Optional, List

from aiomysql import Connection, Cursor, Pool

from models.mysql import SQLEntryPoint, StatementEnum


# noinspection SqlNoDataSourceInspection
class StatisticStatements(StatementEnum):

    UPDATE_STATISTICS: str = (
        """
        UPDATE statistics 
        SET 
            comments = comments + %s, 
            experience = experience + %s, 
            coins = coins + %s
        WHERE viewer_id='%s' AND streamer_id='%s'
        """
    )

    INSERT_STATISTIC: str = (
        """
        INSERT INTO statistics (viewer_id, streamer_id) 
        VALUES ('%s', '%s')
        """
    )

    GET_USER_STATISTICS: str = (
        """
        SELECT comments, experience, coins 
        FROM statistics 
        WHERE viewer_id='%s' AND streamer_id='%s'
        """
    )

    GET_ALL_STATISTICS: str = (
        """
        SELECT viewer_id, comments, experience, coins 
        FROM statistics 
        WHERE streamer_id='%s'
        ORDER BY experience DESC
        """
    )


class StatisticSQL:

    def __init__(self, pool: Pool):
        self.pool: Pool = pool
        self.connection: Optional[Connection] = None
        self.cursor: Optional[Cursor] = None

    async def __create_if_not_exists(self, viewer_id: str, streamer_id: str):
        try:
            await self.cursor.execute(StatisticStatements.INSERT_STATISTIC % (viewer_id, streamer_id))
            await self.connection.commit()
        except:
            logging.error(traceback.format_exc())
            pass

    async def __stats_exist(self, viewer_id: str, streamer_id: str) -> bool:
        try:
            await self.cursor.execute(StatisticStatements.GET_USER_STATISTICS % (viewer_id, streamer_id))
            result = await self.cursor.fetchone()
            return bool(result)
        except:
            pass

        return False

    @SQLEntryPoint
    async def update_statistics(self, viewer_id: str, streamer_id: str, add_comments: int, add_experience: int, add_coins: int):

        if not await self.__stats_exist(viewer_id, streamer_id):
            await self.__create_if_not_exists(viewer_id, streamer_id)

        await self.cursor.execute(StatisticStatements.UPDATE_STATISTICS % (add_comments, add_experience, add_coins, viewer_id, streamer_id))

    @SQLEntryPoint
    async def get_statistics(self, streamer_id: str):
        await self.cursor.execute(StatisticStatements.GET_ALL_STATISTICS % streamer_id)
        return await self.cursor.fetchmany(size=100)

