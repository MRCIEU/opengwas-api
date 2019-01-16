from resources._globals import *
from resources._logger import *
import flask


def close_db(error):
    logging.info("Closing neo4j session")
    if hasattr(flask.g, 'neo4j_db'):
        flask.g.neo4j_db.close()


def get_db():
    if not hasattr(flask.g, 'neo4j_db'):
        flask.g.neo4j_db = dbConnection.session()
    return flask.g.neo4j_db


def clear_db():
    tx = get_db()
    tx.run("MATCH (n) OPTIONAL MATCH (n)-[r]-() DELETE n,r;")


# TODO study id should be study_id not id (collision with neo internals)
def install_index():
    tx = get_db()
    tx.run("CREATE CONSTRAINT ON (n:User) ASSERT n.uid IS UNIQUE;")
    tx.run("CREATE CONSTRAINT ON (n:Group) ASSERT n.gid IS UNIQUE;")
    tx.run("CREATE CONSTRAINT ON (n:Study) ASSERT n.study_id IS UNIQUE;")


def study_info(study_list):
    print(study_list)
    study_data = {}
    # SQL   = "SELECT * FROM study_e where id in ('"+str(",".join(study_list))+"');"
    if study_list == 'snp_lookup':
        SQL = "SELECT * FROM study_e, permissions_e where study_e.id = permissions_e.study_id and permissions_e.gid = 1;"
    else:
        SQL = "SELECT * FROM study_e where id in (" + study_list + ");"

    logger2.debug(SQL)
    query = PySQLPool.getNewQuery(dbConnection)
    query.Query(SQL)
    for q in query.record:
        study_data[q['id']] = q
    # logger2.debug(study_data)
    logger2.debug('study_info:' + str(len(study_data)))
    return study_data


def snp_info(snp_list, type):
    snp_data = {}
    if type == 'id_to_rsid':
        SQL = "SELECT * FROM snp where id in (" + str(",".join(snp_list)) + ");"
    else:
        SQL = "SELECT * FROM snp where name in (" + str(",".join(snp_list)) + ");"
    # logger2.debug(SQL)
    start = time.time()
    query = PySQLPool.getNewQuery(dbConnection)
    query.Query(SQL)
    for q in query.record:
        snp_data[q['id']] = q['name']
    end = time.time()
    t = round((end - start), 4)
    logger2.debug('snp_info:' + str(len(snp_data)) + ' in ' + str(t) + ' seconds')
    return snp_data


# create list of studies available to user
def email_query_list(user_email):
    qList = []
    logger2.debug("getting credentials for " + user_email)
    SQL = """select id from study_e c where (c.id IN (select d.id from study_e d, memberships m, permissions_e p
		WHERE m.uid = "{0}"
		AND p.gid = m.gid
		AND d.id = p.study_id
		)
		OR c.id IN (select d.id from study_e d, permissions_e p
		WHERE p.gid = 1
		AND d.id = p.study_id
		))""".format(user_email)
    SQL2 = """select id from study_e""".format(user_email)
    # logger2.debug(SQL)
    query = PySQLPool.getNewQuery(dbConnection)
    query.Query(SQL)
    for q in query.record:
        qList.append(q['id'])
    logger2.debug('access to ' + str(len(qList)) + ' studies')
    return qList
