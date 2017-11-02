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
    name = attr.ib(default=None)
    updated = attr.ib(default=None)


async def get_voxels(x, y, range, db):
    results = db.data.find({'x': {'$gt': x - range, '$lt': x + range},
                            'y': {'$gt': y - range, '$lt': y + range}},
                           projection={'_id': False, 'updated': False})
    data = []
    async for result in results:
        if not result.get('name'):
            result.pop('name', None)
        data.append(result)

    return data


def verify_payload(payload):
    if any(key not in {'x', 'y', 'z', 'owner', 'name'} for key in payload.keys()):
        return False
    if any([payload[i] < 0 for i in ['x', 'y', 'z']]):
        return False
    if payload['x'] > config.max_x or payload['y'] > config.max_y or payload['z'] > config.max_z:
        return False
    return True


async def store_voxel(voxel: Voxel, app):
    db = app['db']
    neighbours = await get_neighbours(db, voxel, 5)

    occupied = space_occupied(voxel, neighbours)
    flag = occupied if occupied.get('name') else None

    if flag and flag.get('owner') != voxel.owner:
        if too_far_from_flag(voxel, neighbours, flag):
            data = response_cleanup(flag)
            raise ValueError(
                {"message": "You must have at least one voxel no farther than 5 spaces from flag",
                 "conflict": data})
        return await capture_flag(voxel, flag, app)

    if occupied:
        data = response_cleanup(occupied)
        raise ValueError({"message": "Space already occupied",
                          "conflict": data})

    near_neighbours = immediate_neighbours(voxel, neighbours)

    conflict = too_close(voxel, near_neighbours)
    if conflict:
        data = response_cleanup(conflict)
        raise ValueError({"message": "Too close to other player's voxels",
                          "conflict": data})

    valid = valid_location(voxel, near_neighbours)
    if not valid:
        data = response_cleanup(attr.asdict(voxel))
        raise ValueError({"message": "Voxel can be placed at ground level "
                                     "or adjacent to your other voxels",
                          "conflict": data})

    near_flag = too_close_to_flag(voxel, neighbours)
    if near_flag:
        data = response_cleanup(near_flag)
        raise ValueError({"message": "Voxels cannot be placed next to a flag",
                          "conflict": data})

    await db.data.insert_one(attr.asdict(voxel))
    return voxel


async def get_neighbours(db, voxel, range):
    cube_volume = (2 * range + 1) ** 3
    return await db.data.find({'x': {'$lte': voxel.x + range, '$gte': voxel.x - range},
                               'y': {'$lte': voxel.y + range, '$gte': voxel.y - range},
                               'z': {'$lte': voxel.z + range, '$gte': voxel.z - range}},
                              projection={'_id': False}).to_list(cube_volume)


def space_occupied(voxel, neighbours):
    curr_voxel = [n for n in neighbours if n['x'] == voxel.x
                  and n['y'] == voxel.y and n['z'] == voxel.z]
    return curr_voxel[0] if curr_voxel else {}


def valid_location(voxel, adjacent):
    return [n for n in adjacent if
            n['y'] == voxel.y and n['z'] == voxel.z or
            n['y'] == voxel.y and n['x'] == voxel.x or
            n['z'] == voxel.z and n['x'] == voxel.x] \
           or voxel.z == 0


def immediate_neighbours(voxel, neighbours):
    return [n for n in neighbours if
            n.get('x') <= voxel.x + 1 and n.get('x') >= voxel.x - 1
            and n.get('y') <= voxel.y + 1 and n.get('y') >= voxel.y - 1
            and n.get('z') <= voxel.z + 1 and n.get('z') >= voxel.z - 1]


def too_close(voxel, adjacent):
    return [n for n in adjacent if n['owner'] != voxel.owner]


def response_cleanup(data):
    if isinstance(data, list):
        for item in data:
            item.pop('name', None)
            item.pop('updated', None)
    else:
        data.pop('name', None)
        data.pop('updated', None)

    return data


async def capture_flag(new_voxel, curr_voxel, app):
    db = app['db']

    if curr_voxel.get('updated'):
        ownership_time = (new_voxel.updated - curr_voxel.get('updated')).total_seconds()
    else:
        ownership_time = 0

    await db.data.update_one({'x': new_voxel.x, 'y': new_voxel.y, 'z': new_voxel.z},
                             {'$set': {'owner': new_voxel.owner, 'updated': new_voxel.updated}})

    await db.leaderboard.update_one({'owner': curr_voxel['owner']},
                                    {'$inc': {'time': ownership_time}},
                                    upsert=True)
    new_voxel.name = curr_voxel['name']
    new_voxel.captured = True
    return new_voxel


def too_close_to_flag(voxel, neighbours):
    flags = [n for n in neighbours if n.get('name')]
    for flag in flags:
        if all([abs(coord) <= 4 for coord in [(voxel.x - flag.get('x')),
                                              (voxel.y - flag.get('y')),
                                              (voxel.z - flag.get('z'))]]):
            return flag
    return None


def too_far_from_flag(voxel, neighbours, flag):
    return all([n.get('owner') != voxel.owner for n in neighbours])


def get_owner_names(users):
    names = {}
    for uid, user in users.items():
        names[user.get('color')] = user.get('name')

    return names


async def get_leaders(app):
    db = app['db']
    names = get_owner_names(app['users'])
    leaderboard = defaultdict(float)
    curr_time = datetime.utcnow()

    leaders = db.leaderboard.find({'owner': {'$ne': '#ff00ff'}}, projection={'_id': False})

    async for leader in leaders:
        leaderboard[leader['owner']] = leader['time']

    results = db.data.find({'name': {'$ne': None}}, projection={'_id': False})
    async for result in results:
        if result.get('updated'):
            leaderboard[result['owner']] += (curr_time - result['updated']).total_seconds()

    return [{'owner': k, 'name': names.get(k, k), 'time': leaderboard[k]} for k in
            sorted(leaderboard, key=leaderboard.get, reverse=True)]
