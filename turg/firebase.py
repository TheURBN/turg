import asyncio
import json

from google.auth.transport.requests import AuthorizedSession
from google.auth import jwt
from google.oauth2 import service_account

from turg.config import Config
from turg.logger import getLogger

logger = getLogger()
config = Config()

scopes = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/firebase.database',
]


async def run_async(func, *args, **kwargs):
    loop = asyncio.get_event_loop()

    return await loop.run_in_executor(None, func, *args, **kwargs)


def get_authed_session():
    logger.info('Get firebase credentials')

    try:
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(config.service_account),
            scopes=scopes,
        )
    except:
        logger.exception('Authenticate in firebase failed')
        raise ValueError()

    return AuthorizedSession(credentials)


async def update_users(app):
    session = await run_async(get_authed_session)
    res = await run_async(
        session.get,
        'https://theurbngame.firebaseio.com/.json'
    )
    data = res.json()

    for uid, user_data in data.items():
        if uid not in app['users']:
            app['users'][uid] = {'color': user_data['color']}
        else:
            app['users'][uid].update({'color': user_data['color']})


async def get_token_payload(token, app):
    payload = jwt.decode(token=token, certs=app['jwt_cers'], audience='theurbngame')

    if not payload['user_id'] in app['users']:
        app['users'][payload['user_id']] = {'name': payload['name']}
    else:
        app['users'][payload['user_id']].update({'name': payload['name']})

    return payload


async def get_user_color(app, uid):
    if uid in app['users'] and 'color' in app['users'][uid]:
        return app['users'][uid]['color']

    await update_users(app)

    return app['users'].get(uid, {}).get('color')


async def get_user_name(app, uid):
    return app['users'].get(uid, {}).get('name')
