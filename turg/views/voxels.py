from aiohttp import web

from turg.config import Config
from turg.logger import getLogger
from turg.models import Voxel, get_voxels, store_voxel_as_root, verify_payload

from turg.views import check_authorization
from turg.views.websocket import broadcast

logger = getLogger()
config = Config()


class Voxels(web.View):
    async def get(self):
        x = int(self.request.query.get('x', 0))
        y = int(self.request.query.get('y', 0))
        range = int(self.request.query.get('range', 25))

        data = await get_voxels(x, y, range, self.request.app['db'])

        return web.json_response(data, status=200)

    @check_authorization
    async def post(self):
        try:
            payload = await self.request.json()
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
            voxel = await store_voxel_as_root(voxel, db)
        except ValueError as e:
            logger.exception(e)
            return web.json_response({'error': {'message': 'Invalid voxel location'}}, status=409)
        else:
            await broadcast(voxel, self.request.app, {'id': None, 'type': 'update'})
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
