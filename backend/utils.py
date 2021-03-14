import logging
from collections.abc import AsyncIterable
from datetime import datetime
from types import SimpleNamespace
from typing import Optional, Union

import jwt
from aiohttp.web_app import Application
from aiohttp.web_urldispatcher import DynamicResource
from alembic.config import Config
from asyncpg import Record
from asyncpgsa import PG
from asyncpgsa.transactionmanager import ConnectionTransactionContextManager
from passlib.hash import sha256_crypt
from sqlalchemy.sql import Select

from backend import settings
from backend.api.schema import UserSchema
from backend.db.models import User


log = logging.getLogger(__name__)


async def setup_pg(app: Application, pg_url: Optional[str] = None) -> PG:
    log.info(f'Connecting to database: {settings.DB_INFO}')

    app['pg'] = PG()
    await app['pg'].init(pg_url or settings.DB_URL)
    await app['pg'].fetchval('SELECT 1')
    log.info(f'Connected to database: {settings.DB_INFO}')

    try:
        yield

    finally:
        log.info(f'Disconnecting from database: {settings.DB_INFO}')
        await app['pg'].pool.close()
        log.info(f'Disconnected from database: {settings.DB_INFO}')


def make_user_password_hash(raw_password: str) -> str:
    """
    Turn a plain-text password into a hash for database storage.
    """
    return sha256_crypt.hash(raw_password)


def check_user_password(raw_password: str, hashed_password: str) -> bool:
    """
    Return a boolean of whether the raw_password was correct.
    """
    return sha256_crypt.verify(raw_password, hashed_password)


def get_jwt_token_for_user(user: Union[dict, Record, User]) -> str:
    """
    Return a jwt token for a given user_data.
    """
    if isinstance(user, User):
        user = UserSchema().dump(user)
    payload_data = {
        'id': user['id'],
        'email': user['email'],
        'username': user['username'],
        'exp': datetime.utcnow() + settings.JWT_EXPIRATION_DELTA
    }
    token = jwt.encode(payload=payload_data, key=settings.JWT_SECRET)
    return token


def make_alembic_config(cmd_opts: SimpleNamespace) -> Config:
    """
    Creates alembic configuration object.
    """
    config = Config(file_=cmd_opts.config, ini_section=cmd_opts.name, cmd_opts=cmd_opts)
    config.set_main_option('script_location', 'db/alembic')
    if cmd_opts.pg_url:
        config.set_main_option('sqlalchemy.url', cmd_opts.pg_url)
    return config


def url_for(path: str, **kwargs) -> str:
    """
    Generates URL for dynamic aiohttp route with included.
    """
    kwargs = {
        key: str(value)  # All values must be str (for DynamicResource)
        for key, value in kwargs.items()
    }
    return str(DynamicResource(path).url_for(**kwargs))


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
