import flask

from resources.globals import Globals
from .status import check_all, count_elastic_records, count_neo4j_datasets


def index():
    status = check_all()
    elastic_counts = count_elastic_records()
    neo4j_counts = count_neo4j_datasets()
    return flask.render_template('api/index.html',
                                 status=status, elastic_counts=elastic_counts, neo4j_counts=neo4j_counts,
                                 root_url=Globals.app_config['root_url'],
                                 user_tiers=Globals.USER_TIERS, user_allowance=Globals.ALLOWANCE_BY_USER_TIER,
                                 jwt_validity=int(Globals.JWT_VALIDITY / 86400))
