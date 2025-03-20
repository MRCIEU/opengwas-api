from flask import request
from flask_limiter.util import get_remote_address
import datetime
import time
import json

from resources.globals import Globals
from queries.redis_queries import RedisQueries


class Logger:
    def log(self, user_uuid, endpoint, start_time, cost_params=None, n_records=0, gwas_id=None, n_snps=0):
        return RedisQueries('log_pubsub').publish_log('log.api.' + Globals.app_config['env'], json.dumps({
            'uuid': user_uuid,
            'ip': get_remote_address(),
            'endpoint': endpoint,
            'cost_params': cost_params,
            'time': int((time.time() - start_time) * 1000),
            'n_records': n_records,
            'gwas_id': gwas_id,
            'n_snps': n_snps,
            'source': request.headers.get('X-API-SOURCE', None)
        }))

    def log_error(self, user_uuid, endpoint, args, error):
        log_timestamp = int(round(time.time() * 1000000))
        RedisQueries('log').add_log(f"api_error.{Globals.app_config['env']}.{endpoint}", log_timestamp, json.dumps({
            'uuid': user_uuid,
            'ip': get_remote_address(),
            'endpoint': endpoint,
            'datetime': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'args': args,
            'error': error,
            'source': request.headers.get('X-API-SOURCE', None)
        }))
        return log_timestamp

    def log_info(self, user_uuid, operation, args, info):
        log_timestamp = int(round(time.time() * 1000000))
        RedisQueries('log').add_log(f"api_info.{Globals.app_config['env']}.{operation}", log_timestamp, json.dumps({
              'uuid': user_uuid,
              'ip': get_remote_address(),
              'operation': operation,
              'datetime': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'args': args,
              'info': info,
              'source': request.headers.get('X-API-SOURCE', None)
          }))
        return log_timestamp

logger = Logger()
