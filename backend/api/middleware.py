import json
import logging
from http import HTTPStatus
from typing import Optional, Mapping

from aiohttp.web_exceptions import HTTPException
from aiohttp.web_middlewares import middleware
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from marshmallow import ValidationError

from backend.api.payloads import JsonPayload


log = logging.getLogger(__name__)
VALIDATION_ERROR_DESCRIPTION = 'Request validation has failed'


def format_http_error(message: Optional[str] = '', status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
                      fields: Optional[Mapping] = None) -> Response:
    """
    Formats the error as an HTTP exception
    """
    status = HTTPStatus(status_code)
    error = {'code': status.name.lower()}

    # Adds fields errors which failed marshmallow validation
    if '{' in message:
        error['message'] = VALIDATION_ERROR_DESCRIPTION
        error['fields'] = json.loads(message)
    # Other errors
    else:
        error['message'] = message or status.description

    # Adds fields errors which failed validation in views
    if fields:
        error['fields'] = fields

    return Response(body={'error': error}, status=status_code)


def handle_validation_error(error: ValidationError):
    """
    Represents a data validation error as an HTTP response.
    """
    return format_http_error(message=VALIDATION_ERROR_DESCRIPTION, status_code=HTTPStatus.BAD_REQUEST,
                             fields=error.messages)


@middleware
async def error_middleware(request: Request, handler):
    try:
        return await handler(request)
    except HTTPException as err:
        # Exceptions that are HTTP responses were deliberately thrown for display to the client.
        # Text exceptions (or exceptions without information) are formatted in JSON
        if not isinstance(err.body, JsonPayload):
            return format_http_error(err.text, err.status_code)
        raise

    except ValidationError as err:
        # Checking for errors in views
        return handle_validation_error(err)

    except Exception:
        # All other exceptions cannot be displayed to the client as an HTTP response
        # and may inadvertently reveal internal information.
        log.exception('Unhandled exception')
        return format_http_error()
