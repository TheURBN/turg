from aiohttp import web
from motor.motor_asyncio import AsyncIOMotorClient

from turg.views import (
    voxels,
    websocket,
)
from turg.config import Config
from turg.logger import getLogger

logger = getLogger(__name__)
config = Config()


def create_app():
    app = web.Application()

    for view in (voxels, websocket):
        routes = view.factory(app)
        routes = routes if isinstance(routes, list) else [routes]
        for route in routes:
            app.router.add_route(**route)

    return app


async def on_start(app):
    client = AsyncIOMotorClient(
        config.db_host,
        config.db_port
    )
    db = client[config.db_name]

    app['db'] = db
    app['db_client'] = client
    app['websockets'] = []


async def on_shutdown(app):
    app['db_client'].close()

    for ws in app['websockets']:
        await ws.close()


app = create_app()
app.on_startup.append(on_start)
app.on_shutdown.append(on_shutdown)