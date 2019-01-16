from resources._neo4j import get_db


# TODO parameter validation
class MemberOfRel:

    def __init__(self, uid, gid):
        self.uid = str(uid)
        self.gid = int(gid)

    def create(self):
        tx = get_db()
        tx.run(
            "MATCH (u:User {uid:{uid}}) "
            "MATCH (g:Group {gid:{gid}}) "
            "MERGE (u)-[:MEMBER_OF]->(g);", {
                "uid": self.uid,
                "gid": self.gid
            }
        )

    def delete(self):
        tx = get_db()
        tx.run(
            "MATCH (u:User {uid:{uid}})-[rel:MEMBER_OF]->(g:Group {gid:{gid}}) DELETE rel;", {
                "uid": self.uid,
                "gid": self.gid
            }
        )
