import attr
from collections import defaultdict
from datetime import datetime

from turg.config import Config
from turg.logger import getLogger

config = Config()
logger = getLogger()


@attr.s
class Voxel(object):

    def __attrs_post_init__(self):
        if self.updated is None:
            self.updated = datetime.utcnow()

    x = attr.ib(convert=int)
    y = attr.ib(convert=int)
    z = attr.ib(convert=int)
    owner = attr.ib()
    capturable = attr.ib(default=False)
    updated = attr.ib(default=None)


async def get_voxels(x, y, range, db):
    results = db.data.find({'x': {'$gt': x - range, '$lt': x + range},
                            'y': {'$gt': y - range, '$lt': y + range}},
                           projection={'_id': False, 'updated': False})
    data = []
    async for result in results:
        if not result.get('capturable'):
            result.pop('capturable', None)
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

    capturable = occupied and occupied[0].get('capturable')

    if capturable and occupied[0].get('owner') != voxel.owner:
        if occupied[0].get('updated'):
            ownership_time = (voxel.updated - occupied[0].get('updated')).total_seconds()
        else:
            ownership_time = 0

        await db.data.update_one({'x': voxel.x, 'y': voxel.y, 'z': voxel.z},
                                 {'$set': {'owner': voxel.owner, 'updated': voxel.updated}})

        await db.leaderboard.update_one({'owner': occupied[0]['owner']},
                                        {'$inc': {'time': ownership_time}},
                                        upsert=True)
        voxel.capturable = True
        return voxel

    conflict = [n for n in neighbours if n['owner'] != voxel.owner]
    logger.info("VOXEL: %s, N: %s", voxel, neighbours)

    if occupied:
        occupied[0].pop('capturable', None)
        occupied[0].pop('updated', None)
        raise ValueError({"message": "Space already occupied",
                          "conflict": occupied[0]})
    if conflict:
        for v in conflict:
            v.pop('capturable', None)
            v.pop('updated', None)
        raise ValueError({"message": "Too close to other player's voxels",
                          "conflict": conflict})

    await db.data.insert_one(attr.asdict(voxel))
    return voxel


async def get_leaders(db):
    leaderboard = defaultdict(float)
    curr_time = datetime.utcnow()

    leaders = db.leaderboard.find(projection={'_id': False})

    async for leader in leaders:
        leaderboard[leader['owner']] = leader['time']

    results = db.data.find({'capturable': True}, projection={'_id': False})
    async for result in results:
        if result.get('updated'):
            leaderboard[result['owner']] += (curr_time - result['updated']).total_seconds()

    return [{'owner': k, 'time': leaderboard[k]} for k in
            sorted(leaderboard, key=leaderboard.get, reverse=True)]
