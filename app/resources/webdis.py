import requests

from .globals import Globals


class Webdis:
    def __init__(self, db_name: str):
        dbs = {
            'phewas_tasks': '0',
            'phewas_cpalleles': '1',
            'phewas_docids': '2'
        }
        self.url = 'http://' + Globals.app_config['redis']['webdis']['host'] + ":" + str(Globals.app_config['redis']['webdis']['port'])
        self.auth = requests.auth.HTTPBasicAuth(Globals.app_config['redis']['webdis']['basic_auth_username'], Globals.app_config['redis']['webdis']['basic_auth_passwd'])
        self.session = requests.Session()
        self.db = dbs[db_name]

    def query(self, command: list):
        """
        Make POST request to Webdis
        :param command: list of a Redis command and its arguments, e.g. ['ZRANGE', 'key_name', '0', '12345']
        :return: result object
        """
        r = self.session.post(self.url, data='{}/{}'.format(self.db, '/'.join([str(c) for c in command])), auth=self.auth, timeout=60)
        assert r.status_code == 200
        return r.json()
