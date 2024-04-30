from flask_limiter.util import get_remote_address
import time


from resources.redis import Redis


class Logger:

    def __init__(self):
        self.r = Redis().conn['log']
        return

    def log(self, uid, endpoint, gwas_id, start_time):
        self.r.xadd('log_api_request', {
            'uid': uid,
            'ip': get_remote_address(),
            'endpoint': endpoint,
            'gwas_id': gwas_id,
            'time_ms': int((time.time() - start_time) * 1000)
        })
        print(self.r.xlen('log_api_request'))
        return

logger = Logger()
