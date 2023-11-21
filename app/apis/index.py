import flask
from .status import check_all, count_elastic_records, count_neo4j_datasets


def index():
    status = check_all()
    elastic_counts = count_elastic_records()
    neo4j_counts = count_neo4j_datasets()
    return flask.render_template('index.html', status=status, elastic_counts=elastic_counts, neo4j_counts=neo4j_counts)
