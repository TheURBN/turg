import logging
from logging import getLogger

logging.basicConfig(
    format='[{asctime:15}] [{name}.{funcName}:{lineno}] {levelname:7} {message}',
    style='{',
    level=logging.DEBUG,
)

__all__ = ['getLogger']
