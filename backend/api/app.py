import logging
from types import AsyncGeneratorType, MappingProxyType
from typing import AsyncIterable, Mapping

from aiohttp import PAYLOAD_REGISTRY
from aiohttp.web_app import Application
from aiohttp_apispec import setup_aiohttp_apispec, validation_middleware

from backend.api import API_VIEWS
from backend.api.middleware import error_middleware
from backend.api.payloads import AsyncGenJSONListPayload, JsonPayload
from backend.api.signaling import sio
from backend.utils import setup_pg

log = logging.getLogger(__name__)


def create_app() -> Application:
    """
    Creates an instance of the application, ready to run.
    """
    app = Application(
        middlewares=[error_middleware, validation_middleware]
    )

    # Connect at start to postgres and disconnect at stop
    app.cleanup_ctx.append(setup_pg)

    # Attach socket.io signaling server
    sio.attach(app)

    # Registering views
    for view in API_VIEWS:
        log.debug(f'Registering view {view} as {view.URL_PATH!r}')
        app.router.add_route('*', view.URL_PATH, view)

    # Swagger documentation
    setup_aiohttp_apispec(app=app, title='Video Calls API', version='v1', url='/api/v1/docs/swagger.json',
                          swagger_path='/api/v1/docs/', request_data_name='validated_data')

    # Automatic json serialization of data in HTTP responses
    PAYLOAD_REGISTRY.register(AsyncGenJSONListPayload,
                              (AsyncGeneratorType, AsyncIterable))
    PAYLOAD_REGISTRY.register(JsonPayload, (Mapping, MappingProxyType))

    return app
