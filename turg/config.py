import os

import yaml

from turg.logger import getLogger

logger = getLogger(__name__)


def str2bool(val):
    if isinstance(val, str):
        return val.lower() in {'yes', 'true'}

    return val


def get_from_env_or_config(config, param, default=None, param_type=None):
    if default and not param_type:
        param_type = type(default)
    elif not default and not param_type:
        param_type = str

    return param_type(os.environ.get(param.upper(), config.get(param, default)))


class Config(object):
    conf_file = None
    mongodb_uri = None
    max_x = None
    max_y = None
    max_z = None
    ping_interval = None
    api_key = None

    def __init__(self):
        Config.load()

    @staticmethod
    def load():

        Config.conf_file = os.environ.get('CONFIG_FILE', '../config.yml')
        try:
            with open(Config.conf_file, 'r') as stream:
                config = yaml.load(stream)
        except Exception as e:
            logger.warning(f"Unable to read config from file: {Config.conf_file} {e}")
            config = dict()

        Config.mongodb_uri = get_from_env_or_config(config, 'mongodb_uri',
                                                    'mongodb://mongo_db:27017/turg_db')

        Config.max_x = get_from_env_or_config(config, 'max_x', 1000)
        Config.max_y = get_from_env_or_config(config, 'max_y', 1000)
        Config.max_z = get_from_env_or_config(config, 'max_z', 100)
        Config.ping_interval = get_from_env_or_config(config, 'ping_interval', 20)

        api_key = get_from_env_or_config(config, 'api_key', None)

        if not api_key or api_key == 'None':
            raise ValueError("api_key parameter is missing in configuration")

        Config.api_key = api_key

        service_account = get_from_env_or_config(config, 'service_account', None)

        if not service_account or service_account == 'None':
            raise ValueError("service_account parameter is missing in configuration")

        Config.service_account = service_account
