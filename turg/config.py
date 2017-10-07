import os
import yaml


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
    db_host = None
    db_port = None
    db_name = None

    def __init__(self, conf_file=None):
        if not Config.db_host:
            self.load(conf_file)

    @staticmethod
    def load(conf_file):
        if conf_file:
            Config.conf_file = conf_file
        else:
            Config.conf_file = os.environ.get('CONFIG_FILE', '../config.yml')

        if not os.path.isfile(Config.conf_file):
            raise IOError(f"Config file not found: {Config.conf_file}")
        with open(Config.conf_file, 'r') as c:
            config = yaml.load(c)

        Config.db_host = get_from_env_or_config(config, 'db_host', 'localhost')
        Config.db_port = get_from_env_or_config(config, 'db_port', 27017)
        Config.db_name = get_from_env_or_config(config, 'db_name', 'healthchecks')
