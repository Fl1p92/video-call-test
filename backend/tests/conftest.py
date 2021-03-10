import uuid
from types import SimpleNamespace

import pytest
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy_utils import create_database, drop_database
from yarl import URL

from backend.api.app import create_app
from backend.db.factories import Session, UserFactory
from backend.db.models import Base
from backend.settings import DB_URL
from backend.utils import make_alembic_config, get_jwt_token_for_user


@pytest.fixture(scope="module")
def postgres_url() -> str:
    """
    Creates a temporary database and yield db_url.
    """
    tmp_name = '.'.join([uuid.uuid4().hex, 'pytest'])
    db_url = str(URL(DB_URL).with_path(tmp_name))
    create_database(db_url)
    try:
        yield db_url
    finally:
        drop_database(db_url)


@pytest.fixture(scope="module")
def alembic_config(postgres_url: str) -> Config:
    """
    Creates a configuration object for alembic, configured for a temporary database.
    """
    cmd_options = SimpleNamespace(config='alembic.ini', name='alembic', pg_url=postgres_url, raiseerr=False, x=None)
    return make_alembic_config(cmd_options)


@pytest.fixture(scope="module")
def pg_engine(postgres_url) -> Engine:
    """
    Creates tables in db to run the test.
    Creates and returns a database engine.
    """
    engine = create_engine(postgres_url)
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
async def db_session(pg_engine: Engine) -> Session:
    """
    Returns the session with connection to the database.
    """
    Session.configure(bind=pg_engine)
    session = Session()
    try:
        yield session
    finally:
        Session.remove()


@pytest.fixture
async def authorized_api_client(db_session, aiohttp_client, aiomisc_unused_port: int, postgres_url: str):
    """
    Returns API test client with authorized user and user object.
    """
    app = create_app(pg_url=postgres_url)
    user = UserFactory()
    db_session.commit()
    jwt_token = get_jwt_token_for_user(user_data={'id': user.id, 'email': user.email, 'username': user.username})
    headers = {'Authorization' : f'Bearer {jwt_token}'}

    client = await aiohttp_client(app, server_kwargs={'port': aiomisc_unused_port}, headers=headers)
    try:
        yield client, user
    finally:
        await client.close()
