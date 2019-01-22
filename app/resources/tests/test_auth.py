from resources._auth import email_query
import pymysql.cursors


def test_email_query():
    connection = pymysql.connect(
        host='ieu-db-interface.epi.bris.ac.uk',
        user='mrbaseapp',
        password='M1st3rbase!',
        port=13306,
        db='mrbase'
    )
    q = """SELECT * FROM study_e c WHERE {0}""".format(email_query('gh13047@brisol.ac.uk'))

    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(q)
            results = cursor.fetchall()
            d=dict()

            for result in results:
                print(result)
    finally:
        connection.close()

    assert True
