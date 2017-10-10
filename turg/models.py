import attr
from datetime import datetime


@attr.s
class Voxel(object):
    x = attr.ib(convert=int)
    y = attr.ib(convert=int)
    z = attr.ib(convert=int)
    owner = attr.ib()
    timestamp = attr.ib(default=datetime.utcnow())
