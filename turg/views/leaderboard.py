from time import time
from aiohttp import web

from turg.config import Config
from turg.logger import getLogger
from turg.models import get_leaders

logger = getLogger()
config = Config()


class Leaders(web.View):
    cache = None
    cache_ts = None

    async def get(self):
        now = time()

        if Leaders.cache is None or now > Leaders.cache_ts + config.cache_seconds:
            Leaders.cache = await get_leaders(self.request.app)
            Leaders.cache_ts = now

        return web.json_response(Leaders.cache, status=200)


def factory(app):
    return {
        'method': 'GET',
        'path': '/v1/leaderboard/',
        'handler': Leaders,
        'expect_handler': web.Request.json,
    }


def cors():
    return {
        'allow_credentials': True,
        'expose_headers': '*',
        'allow_headers': '*'
    }
