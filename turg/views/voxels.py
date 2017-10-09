import attr

from aiohttp import web

from pymongo.errors import DuplicateKeyError

from turg.models import Voxel


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
        except DuplicateKeyError:
            return web.json_response({'error': {'message': 'Already occupied'}}, status=409)
        except ValueError:
            return web.json_response({'error': {'message': 'Invalid voxel location'}}, status=400)
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
    if not all([s in payload for s in ('x', 'y', 'z', 'owner')]):
        return False
    if not all([isinstance(payload[s], int) and payload[s] <= 1000 and payload[s] >= 0 for s in
                ['x', 'y', 'z', 'owner']]):
        return False
    if set(payload.keys()) != {'x', 'y', 'z', 'owner'}:
        return False
    return True


async def store_voxel(voxel: Voxel, db):
    neighbours = await db.data.find({'x': {'$lte': voxel.x + 1, '$gte': voxel.x - 1},
                                     'y': {'$lte': voxel.y + 1, '$gte': voxel.y - 1},
                                     'z': {'$lte': voxel.z + 1, '$gte': voxel.z - 1}},
                                    projection={'_id': False}).to_list(50)

    adjacent = [n for n in neighbours if
                n['y'] == voxel.y and n['z'] == voxel.z or
                n['y'] == voxel.y and n['x'] == voxel.x or
                n['z'] == voxel.z and n['x'] == voxel.x
                ]

    if not adjacent and voxel.z != 0:
        raise ValueError("Invalid voxel location")

    await db.data.insert_one(attr.asdict(voxel))
