from aiohttp import web

from turg.config import Config
from turg.logger import getLogger
from turg.models import get_leaders

logger = getLogger()
config = Config()


class Leaders(web.View):
    async def get(self):
        data = await get_leaders(self.request.app['db'])

        return web.json_response(data, status=200)


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
