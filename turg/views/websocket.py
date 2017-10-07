from aiohttp import web, WSMsgType
from aiohttp.web import WebSocketResponse


class WebSocket(web.View):
    async def get(self):
        ws = WebSocketResponse()
        await ws.prepare(self.request)

        self.request.app['websockets'].append(ws)

        async for msg in ws:
            if msg.tp == WSMsgType.text:
                if msg.data == 'close':
                    await ws.close()
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
