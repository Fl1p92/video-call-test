import logging
from types import AsyncGeneratorType, MappingProxyType
from typing import AsyncIterable, Mapping

from aiohttp import PAYLOAD_REGISTRY
from aiohttp.web_app import Application
from aiohttp_apispec import validation_middleware, AiohttpApiSpec
from aiohttp_jwt import JWTMiddleware

from backend import settings
from backend.api import API_VIEWS, JWT_WHITE_LIST
from backend.api.middleware import error_middleware
from backend.api.payloads import AsyncGenJSONListPayload, JsonPayload
from backend.api.signaling import sio
from backend.utils import setup_pg


log = logging.getLogger(__name__)
docs_path = '/api/v1/docs/'
jwt_middleware = JWTMiddleware(secret_or_pub_key=settings.JWT_SECRET,
                               whitelist=(f'{docs_path}.*', ) + JWT_WHITE_LIST,
                               algorithms=["HS256"])


def create_app() -> Application:
    """
    Creates an instance of the application, ready to run.
    """
    app = Application(
        middlewares=[error_middleware, jwt_middleware, validation_middleware]
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
    api_spec = AiohttpApiSpec(app=app, title='Video Calls API', version='v1', request_data_name='validated_data',
                              swagger_path=docs_path, url=f'{docs_path}swagger.json', static_path=f'{docs_path}static')
    # Manual add Authorize header to swagger
    api_key_scheme = {"type": "apiKey", "in": "header", "name": "Authorization"}
    api_spec.spec.components.security_scheme('JWT Authorization', api_key_scheme)


    # Automatic json serialization of data in HTTP responses
    PAYLOAD_REGISTRY.register(AsyncGenJSONListPayload,
                              (AsyncGeneratorType, AsyncIterable))
    PAYLOAD_REGISTRY.register(JsonPayload, (Mapping, MappingProxyType))

    return app
