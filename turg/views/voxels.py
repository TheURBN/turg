import attr
from aiohttp import web

from turg.models import Voxel
from turg.config import Config
from turg.logger import getLogger

logger = getLogger()
config = Config()


class Voxels(web.View):
    async def get(self):
        x = int(self.request.query.get('x', 0))
        y = int(self.request.query.get('y', 0))
        range = int(self.request.query.get('range', 25))

        db = self.request.app['db']
        results = db.data.find({'x': {'$gt': x - range, '$lt': x + range},
                                'y': {'$gt': y - range, '$lt': y + range}},
                               projection={'_id': False})
        data = []
        async for result in results:
            result['timestamp'] = result['timestamp'].isoformat()
            data.append(result)

        return web.json_response(data, status=200)

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


def verify_payload(payload):
    if set(payload.keys()) != {'x', 'y', 'z', 'owner'}:
        return False
    if any([payload[i] < 0 for i in ['x', 'y', 'z']]):
        return False
    if payload['x'] > config.max_x or payload['y'] > config.max_y or payload['z'] > config.max_z:
        return False
    return True


async def store_voxel(voxel: Voxel, db):
    neighbours = await db.data.find({'x': {'$lte': voxel.x + 1, '$gte': voxel.x - 1},
                                     'y': {'$lte': voxel.y + 1, '$gte': voxel.y - 1},
                                     'z': {'$lte': voxel.z + 1, '$gte': voxel.z - 1}},
                                    projection={'_id': False}).to_list(50)

    occupied = [n for n in neighbours if n['x'] == voxel.x
                and n['y'] == voxel.y and n['z'] == voxel.z]

    conflict = [n for n in neighbours if n['owner'] != voxel.owner]

    if occupied or conflict:
        raise ValueError("Invalid voxel location")

    await db.data.insert_one(attr.asdict(voxel))
