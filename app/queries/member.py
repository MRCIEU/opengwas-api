from resources._neo4j import get_db


# TODO parameter validation
class Member:

    def __init__(self, uid, gid):
        self.uid = str(uid)
        self.gid = int(gid)

    def create(self):
        tx = get_db()
        tx.run(
            "MATCH (u:User {uid:{uid}}) "
            "MATCH (g:Group {gid:{gid}}) "
            "MERGE (u)-[:MEMBER_OF]->(g);", {
                "sid": self.uid,
                "gid": self.gid
            }
        )

    def delete(self):
        tx = get_db()
        tx.run(
            "MATCH (u:User {uid:{uid}})-[rel:MEMBER_OF]->(g:Group {gid:{gid}}) DELETE rel;", {
                "sid": self.uid,
                "gid": self.gid
            }
        )
