import logging
from collections import AsyncIterable

from aiohttp.web_app import Application
from asyncpgsa import PG
from asyncpgsa.transactionmanager import ConnectionTransactionContextManager
from sqlalchemy import Numeric, cast, func
from sqlalchemy.sql import Select

from backend import settings


log = logging.getLogger(__name__)


async def setup_pg(app: Application) -> PG:
    log.info(f'Connecting to database: {settings.DB_INFO}')

    app['pg'] = PG()
    await app['pg'].init(settings.DB_URL)
    await app['pg'].fetchval('SELECT 1')
    log.info(f'Connected to database: {settings.DB_INFO}')

    try:
        yield

    finally:
        log.info(f'Disconnecting from database: {settings.DB_INFO}')
        await app['pg'].pool.close()
        log.info(f'Disconnected from database: {settings.DB_INFO}')


def rounded(column, fraction: int = 2):
    return func.round(cast(column, Numeric), fraction)


class SelectQuery(AsyncIterable):
    """
    Used to send data from PostgreSQL to client immediately after receiving,
    in parts, without buffering all the data.
    """
    PREFETCH = 1000

    __slots__ = (
        'query', 'transaction_ctx', 'prefetch', 'timeout'
    )

    def __init__(self, query: Select,
                 transaction_ctx: ConnectionTransactionContextManager,
                 prefetch: int = None,
                 timeout: float = None):
        self.query = query
        self.transaction_ctx = transaction_ctx
        self.prefetch = prefetch or self.PREFETCH
        self.timeout = timeout

    async def __aiter__(self):
        async with self.transaction_ctx as conn:
            cursor = conn.cursor(self.query, prefetch=self.prefetch, timeout=self.timeout)
            async for row in cursor:
                yield row
