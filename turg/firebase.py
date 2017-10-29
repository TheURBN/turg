import os
import json
import asyncio

from google.oauth2 import service_account
from google.auth import jwt
from google.auth.transport.requests import AuthorizedSession

from turg.logger import getLogger
from turg.config import Config

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
            app['users'][uid] = user_data['color']


async def get_user_id(token, certs):
    payload = jwt.decode(token=token, certs=certs, audience='theurbngame')
    return payload['user_id']


async def get_user_color(app, uid):
    if uid in app['users']:
        return app['users'][uid]

    await update_users(app)

    return app['users'].get(uid)
