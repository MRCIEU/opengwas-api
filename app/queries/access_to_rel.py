from resources._neo4j import get_db


class AccessToRel:

    def __init__(self, gid, study_id):
        self.study_id = int(study_id)
        self.gid = int(gid)

    def create(self):
        tx = get_db()
        tx.run(
            "MATCH (s:Study {study_id:{study_id}}) "
            "MATCH (g:Group {gid:{gid}}) "
            "MERGE (g)-[:ACCESS_TO]->(s);", {
                "study_id": self.study_id,
                "gid": self.gid
            }
        )

    def delete(self):
        tx = get_db()
        tx.run(
            "MATCH (g:Group {gid:{gid}})-[rel:ACCESS_TO]->(s:Study {study_id:{study_id}}) DELETE rel;", {
                "study_id": self.study_id,
                "gid": self.gid
            }
        )
