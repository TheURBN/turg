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
