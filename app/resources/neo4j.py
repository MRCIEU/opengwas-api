import flask
import logging

from resources.globals import Globals

logger = logging.getLogger('debug-log')


class Neo4j:

    @staticmethod
    def close_db(error):
        logger.info("Closing neo4j session")
        if hasattr(flask.g, 'neo4j_db'):
            flask.g.neo4j_db.close()

    @staticmethod
    def get_db():
        if not hasattr(flask.g, 'neo4j_db'):
            flask.g.neo4j_db = Globals.neo4j_driver.session()
        return flask.g.neo4j_db

    # @staticmethod
    # def clear_db():
    #     tx = Neo4j.get_db()
    #     tx.run("MATCH (n) OPTIONAL MATCH (n)-[r]-() DELETE n,r;")

    # @staticmethod
    # def drop_all_constraints():
    #     tx = Neo4j.get_db()
    #     cmd = []
    #     results = tx.run("SHOW CONSTRAINTS;")
    #     for result in results:
    #         cmd.append("DROP CONSTRAINT " + result['name'])
    #     for c in cmd:
    #         tx.run(c)

    @staticmethod
    def check_running():
        try:
            tx = Neo4j.get_db()
            tx.run("MATCH (n) RETURN n LIMIT 0;")
            return 'Operational'
        except Exception as e:
            print(e)
        return 'Unavailable'
