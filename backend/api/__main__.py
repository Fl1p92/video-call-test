import logging

from aiohttp import web
from aiomisc.log import basic_config

from backend import settings
from backend.api.app import create_app


def main():
    app = create_app()
    basic_config(logging.DEBUG, buffered=True)
    web.run_app(app, port=settings.BACKEND_PORT)


if __name__ == '__main__':
    main()
