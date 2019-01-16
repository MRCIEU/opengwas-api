from resources._neo4j import get_db


# TODO parameter validation
class Access:

    def __init__(self, gid, sid):
        self.sid = int(sid)
        self.gid = int(gid)

    def create(self):
        tx = get_db()
        tx.run(
            "MATCH (s:Study {sid:{sid}}) "
            "MATCH (g:Group {gid:{gid}}) "
            "MERGE (g)-[:ACCESS_TO]->(s);", {
                "sid": self.sid,
                "gid": self.gid
            }
        )

    def delete(self):
        tx = get_db()
        tx.run(
            "MATCH (g:Group {gid:{gid}})-[rel:ACCESS_TO]->(s:Study {sid:{sid}}) DELETE rel;", {
                "sid": self.sid,
                "gid": self.gid
            }
        )
