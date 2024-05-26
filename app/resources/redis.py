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
        conf = Globals.app_config['redis']
        self.pool = {
            'session': redis.ConnectionPool(host=conf['oci']['host'], port=conf['oci']['port'], password=conf['oci']['pass'], db=0),
            'limiter': redis.ConnectionPool(host=conf['oci']['host'], port=conf['oci']['port'], password=conf['oci']['pass'], db=1)
            # 'phewas_tasks': redis.ConnectionPool(host=conf['ieu-db']['host'], port=conf['ieu-db']['port'], password=conf['ieu-db']['pass'], db=0),
            # 'phewas_cpalleles': redis.ConnectionPool(host=conf['ieu-db']['host'], port=conf['ieu-db']['port'], password=conf['ieu-db']['pass'], db=1),
            # 'phewas_docids': redis.ConnectionPool(host=conf['ieu-db']['host'], port=conf['ieu-db']['port'], password=conf['ieu-db']['pass'], db=2)
        }

    @property
    def conn(self):
        if not hasattr(self, '_conn'):
            self.get_connection()
        return self._conn

    def get_connection(self):
        self._conn = {
            'session': redis.Redis(connection_pool=self.pool['session']),
            'limiter': redis.Redis(connection_pool=self.pool['limiter']),
            'log': redis.Redis(connection_pool=self.pool['session'])  # Pub/Sub is not DB-specific
            # 'phewas_tasks': redis.Redis(connection_pool=self.pool['phewas_tasks']),
            # 'phewas_cpalleles': redis.Redis(connection_pool=self.pool['phewas_cpalleles']),
            # 'phewas_docids': redis.Redis(connection_pool=self.pool['phewas_docids'])
        }
