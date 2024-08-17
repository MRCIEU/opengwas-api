import requests
from urllib3.util import Retry
from requests.adapters import HTTPAdapter

from .globals import Globals


class RedisProxy:
    def __init__(self, db_name: str):
        dbs = {
            'phewas_tasks': '0',
            'phewas_cpalleles': '1',
            'phewas_docids': '2'
        }
        self.url = 'http://' + Globals.app_config['redis']['ieu-ssd-proxy']['host'] + ":" + str(Globals.app_config['redis']['ieu-ssd-proxy']['port'])
        self.auth = requests.auth.HTTPBasicAuth(Globals.app_config['redis']['ieu-ssd-proxy']['basic_auth_username'], Globals.app_config['redis']['ieu-ssd-proxy']['basic_auth_passwd'])

        self.session_with_retry = requests.Session()
        self.session_with_retry.mount('http://', HTTPAdapter(max_retries=Retry(
            total=10,
            backoff_factor=1,
            allowed_methods=None  # Retry on any verb
        )))

        self.session = requests.Session()

        self.db = dbs[db_name]

    def query(self, commands: list[dict], retry=True):
        """
        Make POST request to Redis proxy
        :param commands: list of a Redis command and its arguments, e.g. [{'cmd': 'zrange', 'args': {'name': 1, 'start': 12345, 'end': 13000, 'byscore': 'True'}}]
        :param retry: True to retry (WARNING! consider idempotence)
        :return: result object
        """
        r = getattr(self, 'session_with_retry' if retry else 'session').post(self.url, json={
            'db': self.db,
            'cmds': commands
        }, auth=self.auth, timeout=60)
        assert r.status_code == 200
        return r.json()
