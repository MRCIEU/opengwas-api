import requests
import logging
from resources.globals import Globals

logger = logging.getLogger('debug-log')


class Cromwell:

    @staticmethod
    def get_version():
        try:
            r = requests.get(Globals.CROMWELL_URL + "/engine/v1/version")
            assert r.status_code == 200
            return r.json()['cromwell']
        except (requests.exceptions.HTTPError, AssertionError, KeyError) as e:
            raise ConnectionError("Could not connect to Cromwell: {}".format(e))
