import redis

from .globals import Globals


# Use singleton for Redis connection pool
# https://stackoverflow.com/questions/49398590/correct-way-of-using-redis-connection-pool-in-python
class Singleton(type):
    """
    A metaclass for singleton purpose. Every singleton class should inherit from this class by 'metaclass=Singleton'.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Redis(metaclass=Singleton):
    def __init__(self):
        host = Globals.app_config['redis']['host']
        port = Globals.app_config['redis']['port']
        password = Globals.app_config['redis']['pass']
        self.pool = {
            'session': redis.ConnectionPool(host=host, port=port, password=password, db=0),
            'limiter': redis.ConnectionPool(host=host, port=port, password=password, db=1),
            'log': redis.ConnectionPool(host=host, port=port, password=password, db=2)
        }

    @property
    def conn(self):
        if not hasattr(self, '_conn'):
            self.getConnection()
        return self._conn

    def getConnection(self):
        self._conn = {
            'session': redis.Redis(connection_pool=self.pool['session']),
            'limiter': redis.Redis(connection_pool=self.pool['limiter']),
            'log': redis.Redis(connection_pool=self.pool['log'])
        }