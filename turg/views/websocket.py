import json
import attr
from aiohttp import web, WSMsgType
from aiohttp.web import WebSocketResponse

from turg.logger import getLogger
from turg.models import get_voxels, verify_payload, store_voxel, Voxel


logger = getLogger()


class WebSocket(web.View):
    async def get(self):
        ws = WebSocketResponse()
        await ws.prepare(self.request)

        self.request.app['websockets'].append(ws)

        async for msg in ws:
            logger.info("MSG: %s", msg)
            if msg.tp == WSMsgType.text:
                if msg.data == 'close':
                    await ws.close()
                else:
                    try:
                        data = json.loads(msg.data)
                    except:
                        pass
                    else:
                        logger.info("Got request: %s", data)
                        await process_request(data, ws, self.request.app)

            elif msg.tp == WSMsgType.error:
                pass

        self.request.app['websockets'].remove(ws)

        return ws


def factory(app):
    return {
        'method': 'GET',
        'path': '/v1/ws/',
        'handler': WebSocket,
        'expect_handler': web.Request.json,
    }


async def process_request(data, ws, app):
    if 'type' not in data or ('args' not in data or not isinstance(data, dict)):
        return {'error': {'message': {'Method and args required'}}}

    _id = data.get('id', None)
    _type = data['type'].lower()
    args = data['args']
    meta = {'id': _id, 'type': _type}

    if _type == 'range':
        await retrieve(args, ws, app, meta)
    elif _type == 'update':
        await place(args, ws, app, meta)
    else:
        await ws.send_json({'error': {'message': {'Unknown method or no method specified'}}})


async def retrieve(args, ws, app, meta):
    x, y, r = args.get('x', 0), args.get('y', 0), args.get('range', 25)
    voxels = await get_voxels(x, y, r, app['db'])
    app['players'][ws] = {'x': x, 'y': y, 'range': r}
    await ws.send_json({'data': voxels, 'meta': meta})


async def place(args, ws, app, meta):
    if not verify_payload(args):
        return await ws.send_json({'error': {'message': 'Invalid payload'}})

    voxel = Voxel(**args)

    try:
        await store_voxel(voxel, app['db'])
    except ValueError as e:
        return await ws.send_json({'error': {'message': str(e)}})
    else:
        return await broadcast(voxel, app, meta)


async def broadcast(voxel, app, meta):
    for ws in app['websockets']:
        position = app['players'].get(ws)
        if not position or in_range(voxel, position):
            try:
                await ws.send_json({'data': attr.asdict(voxel), 'meta': meta})
            except:
                logger.info("Failed to send update to socket %s", id(ws))


def in_range(voxel, position):
    x, y, r = position.get('x', 0), position.get('y', 0), position.get('range', 25)
    x_in_range = voxel.x > x - r and voxel.x < x + r
    y_in_range = voxel.y > y - r and voxel.y < y + r

    return x_in_range and y_in_range
