from aiohttp import web

from turg.config import Config
from turg.logger import getLogger
from turg.models import Voxel, get_voxels, store_voxel, verify_payload

logger = getLogger()
config = Config()


class Voxels(web.View):
    async def get(self):
        x = int(self.request.query.get('x', 0))
        y = int(self.request.query.get('y', 0))
        range = int(self.request.query.get('range', 25))

        data = await get_voxels(x, y, range, self.request.app['db'])

        return web.json_response(data, status=200)

    async def post(self):
        try:
            payload = await self.request.json()
            payload.pop('name', None)
            if not verify_payload(payload):
                raise ValueError("Incorrect payload")
            voxel = Voxel(**payload)
        except Exception as e:
            return web.json_response(
                {'error': str(e)},
                status=400
            )

        db = self.request.app['db']

        try:
            await store_voxel(voxel, db)
        except ValueError:
            return web.json_response({'error': {'message': 'Invalid voxel location'}}, status=409)
        else:
            return web.json_response({'status': 'ok'}, status=200)


def factory(app):
    return [
        {
            'method': 'GET',
            'path': '/v1/voxels/',
            'handler': Voxels,
            'expect_handler': web.Request.json,
        },
        {
            'method': 'POST',
            'path': '/v1/voxels/',
            'handler': Voxels,
            'expect_handler': web.Request.json,
        },
    ]
