import attr

from turg.config import Config
from turg.logger import getLogger

config = Config()
logger = getLogger()


@attr.s
class Voxel(object):
    x = attr.ib(convert=int)
    y = attr.ib(convert=int)
    z = attr.ib(convert=int)
    owner = attr.ib()


async def get_voxels(x, y, range, db):
    results = db.data.find({'x': {'$gt': x - range, '$lt': x + range},
                            'y': {'$gt': y - range, '$lt': y + range}},
                           projection={'_id': False})
    data = []
    async for result in results:
        data.append(result)

    return data


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
    logger.info("VOXEL: %s, N: %s", voxel, neighbours)
    if occupied or conflict:
        raise ValueError("Invalid voxel location")

    await db.data.insert_one(attr.asdict(voxel))
