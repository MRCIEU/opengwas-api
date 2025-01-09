import flask

from resources.globals import Globals
from .status import check_all, count_elastic_records, count_neo4j_datasets


def index():
    return flask.render_template('api/index.html',
                                 root_url=Globals.app_config['root_url'],
                                 user_tiers=Globals.USER_TIERS, user_allowance=Globals.ALLOWANCE_BY_USER_TIER,
                                 jwt_validity=int(Globals.JWT_VALIDITY / 86400))
