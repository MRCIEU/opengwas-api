from flask import request
from flask_limiter.util import get_remote_address
import time
import json

from resources.globals import Globals
from resources.redis import Redis


class Logger:

    def __init__(self):
        self.r = Redis().conn['log']
        return

    def log(self, uid, endpoint, start_time, cost_params=None, n_records=0, gwas_id=None, n_snps=0):
        subscribers = self.r.publish('log.api.' + Globals.app_config['env'], json.dumps({
            'uid': uid,
            'ip': get_remote_address(),
            'endpoint': endpoint,
            'cost_params': cost_params,
            'time': int((time.time() - start_time) * 1000),
            'n_records': n_records,
            'gwas_id': gwas_id,
            'n_snps': n_snps,
            'source': request.headers.get('X-API-SOURCE', None)
        }))
        return subscribers


logger = Logger()
