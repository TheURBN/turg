import json
import attr
import time
from aiohttp import web, WSMsgType
from aiohttp.web import WebSocketResponse

from turg.config import Config
from turg.logger import getLogger
from turg.models import get_voxels, verify_payload, store_voxel, Voxel
from turg.firebase import get_token_payload, get_user_color

logger = getLogger()
config = Config()


def get_ws_by_id(_id, app):
    for item in app['websockets']:
        if id(item) == _id:
            return item

    return None


async def close_old_user_connections(color, app):
    old_ws_id = app['colors_websocket'][color]
    old_ws = get_ws_by_id(old_ws_id, app)

    if old_ws:
        logger.info("Close old WS connections for %s", color)

        await old_ws.close()

        if old_ws in app['websockets']:
            app['websockets'].remove(old_ws)

        app['websockets_colors'].pop(id(old_ws), None)
        app['colors_websocket'].pop(color, None)


class WebSocket(web.View):
    async def get(self):
        app = self.request.app

        try:
            token = self.request.query['token']
        except KeyError:
            logger.exception("Data not valid")
            return web.json_response(
                {'error': {'message': 'Data not valid'}}, status=400)

        try:
            payload = await get_token_payload(token, app)
            uid = payload['user_id']
            name = payload['name']
        except ValueError as e:
            logger.exception("Can't get token payload")
            return web.json_response(
                {'error': {'message': str(e)}}, status=401)

        try:
            color = await get_user_color(app, uid)
        except ValueError:
            logger.exception("Can't get color info")
            return web.json_response(
                {'error': {'message': 'Can\'t get color info'}}, status=500)

        if not color:
            logger.exception("No user color")
            return web.json_response(status=401)

        if color in app['colors_websocket']:
            await close_old_user_connections(color, app)

        ws = WebSocketResponse(compress=True)
        await ws.prepare(self.request)

        app['websockets'].append(ws)
        app['colors_websocket'][color] = id(ws)
        app['websockets_colors'][id(ws)] = color

        await ws.send_json({
            'data': {'color': color},
            'meta': {'type': 'userColor'},
        })
        await user_login_broadcast(name, app)

        ratelimiter = app['limiter']

        async for msg in ws:
            logger.info("MSG: %s", msg)
            if ratelimiter.limit_exceeded(uid):
                logger.error("Rate limit for user %s exceeded", uid)
                msg = f'Requests limit of {ratelimiter.requests} per minute exceeded'
                await ws.send_json({'error': {'message': msg}})
                continue
            if msg.tp == WSMsgType.text:
                if msg.data == 'close':
                    logger.info("Close ws connection")
                    await ws.close()
                else:
                    try:
                        data = json.loads(msg.data)
                    except:
                        pass
                    else:
                        logger.info("Got request: %s", data)
                        await process_request(data, ws, app, name)

            elif msg.tp == WSMsgType.error:
                logger.exception("Got ws error %s", id(ws))

        if ws in app['websockets']:
            app['websockets'].remove(ws)

        app['websockets_colors'].pop(id(ws), None)
        app['colors_websocket'].pop(color, None)

        await user_logout_broadcast(name, app)

        return ws


def factory(app):
    return {
        'method': 'GET',
        'path': '/v1/ws/',
        'handler': WebSocket,
        'expect_handler': web.Request.json,
    }


async def process_request(data, ws, app, name):
    if not isinstance(data, dict) or 'type' not in data or 'args' not in data:
        return {'error': {'message': {'Method and args required'}}}

    _id = data.get('id', None)
    _type = data['type'].lower()
    args = data['args']
    meta = {'id': _id, 'type': _type}

    if _type == 'range':
        await retrieve(args, ws, app, meta)
    elif _type == 'update':
        await place(args, ws, app, meta, name)
    else:
        await ws.send_json({
            'error': {'message': {'Unknown method or no method specified'}},
            'meta': meta,
        })


async def retrieve(args, ws, app, meta):
    start_time = time.time()
    x, y, r = args.get('x', 0), args.get('y', 0), args.get('range', 25)

    if r <= 0:
        r = 25
    elif r > config.max_range:
        r = config.max_range

    voxels = await get_voxels(x, y, r, app['db'])

    logger.info("Get voxels for range (x - %s, y - %s, range - %s) – (%.02fs)",
                x, y, r, time.time() - start_time)

    await ws.send_json({'data': voxels, 'meta': meta})


async def place(args, ws, app, meta, name):
    start_time = time.time()
    args.pop('name', None)
    if not verify_payload(args):
        return await ws.send_json({
            'error': {'message': 'Invalid payload'},
            'meta': meta,
        })

    try:
        args['owner'] = app['websockets_colors'][id(ws)]
        logger.info('WS color: %s', args['owner'])
        voxel = await store_voxel(Voxel(**args), app)
        logger.info("Store voxel – (%.02fs)",
                    time.time() - start_time)
    except (ValueError, KeyError) as e:
        res = {
            'error': {'message': str(e)},
            'meta': meta,
        }
        if e.args and isinstance(e.args[0], dict):
            res['error'] = e.args[0]
        return await ws.send_json(res)
    else:
        if getattr(voxel, 'captured', None):
            await broadcast(voxel, app, meta)
            return await flag_captured(name, voxel.name, app)

        return await broadcast(voxel, app, meta)


async def flag_captured(name, flag, app):
    await broadcast({
        'name': name,
        'flag': flag,
    }, app, {
        'type': 'flagCaptured',
    })


async def user_login_broadcast(name, app):
    await broadcast({
        'name': name,
    }, app, {
        'type': 'userLogin',
    })


async def user_logout_broadcast(name, app):
    await broadcast({
        'name': name,
    }, app, {
        'type': 'userLogout',
    })


async def broadcast(data, app, meta):
    if not isinstance(data, dict):
        data = attr.asdict(data)
        data.pop('updated', None)
        if not data.get('name'):
            data.pop('name', None)

    for ws in app['websockets']:
        try:
            await ws.send_json({'data': data, 'meta': meta})
            logger.info("Broadcast data %s for %s", meta.get('id'), id(ws))
        except:
            logger.exception("Failed to send update to socket %s", id(ws))


def in_range(voxel, position):
    x, y, r = position.get('x', 0), position.get('y', 0), position.get('range', 25)
    x_in_range = x - r < voxel.x < x + r
    y_in_range = y - r < voxel.y < y + r

    return x_in_range and y_in_range
