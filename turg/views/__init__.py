from aiohttp import web
import hmac

from turg.config import Config

config = Config()


async def ws_notify(app, what):
    for ws in app.get('websockets', []):
        await ws.send_json(what)


def check_authorization(f):
    async def wrapper(*args, **kwargs):
        this = args[0]
        auth = this.request.headers.get('Authorization', '')
        if not hmac.compare_digest(auth, config.api_key):
            return web.json_response(status=401)
        return await f(*args, **kwargs)
    return wrapper
