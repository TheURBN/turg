from aiohttp import web


class Voxels(web.View):
    async def get(self):
        return web.json_response({'status': 'ok'}, status=200)


def factory(app):
    return {
        'method': 'GET',
        'path': '/v1/voxels/',
        'handler': Voxels,
        'expect_handler': web.Request.json,
    }
