from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from resources.globals import Globals

limiter = Limiter(
    key_func=get_remote_address,
    strategy='fixed-window-elastic-expiry',
    storage_uri='redis://:' + Globals.app_config['redis']['pass'] + '@' + Globals.app_config['redis']['host'] + ':' + Globals.app_config['redis']['port'],
)
