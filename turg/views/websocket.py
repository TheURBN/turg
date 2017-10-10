import json
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
        db = self.request.app['db']

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
                        result = await process_request(data, db)
                        ws.send_json(result)

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


async def process_request(data, db):
    if 'method' not in data or ('args' not in data or not isinstance(data, dict)):
        return {'error': {'message': {'Method and args required'}}}

    method = data['method'].lower()
    args = data['args']

    if method == 'get':
        return await get_voxels(args.get('x', 0), args.get('y', 0), args.get('range', 25), db)
    elif method == 'post':
        if not verify_payload(args):
            return {'error': {'message': 'Invalid payload'}}
        voxel = Voxel(**args)
        try:
            await store_voxel(voxel, db)
        except ValueError as e:
            return {'error': {'message': str(e)}}
        else:
            return {'status': 'ok'}
    else:
        return {'error': {'message': {'Unknown method or no method specified'}}}
