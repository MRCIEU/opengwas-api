import unittest
from resources._neo4j import *

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

"""Test neo4j methods"""


class TestNeo4j(unittest.TestCase):
    app = flask.Flask(__name__)

    def test_study_info(self):
        with self.app.app_context():
            tx = get_db()
            results = tx.run('MATCH (s:Study) WHERE s.id = {id} RETURN s', id=1015)

    if __name__ == '__main__':
        unittest.main()
