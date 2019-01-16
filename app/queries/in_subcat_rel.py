from resources._neo4j import get_db


class InSubcatRel:

    def __init__(self, study_id, name):
        self.study_id = str(study_id)
        self.name = str(name)

    def create(self):
        tx = get_db()
        tx.run(
            "MATCH (s:Study {study_id:{study_id}}) "
            "MATCH (c:Subcategory {name:{name}}) "
            "MERGE (s)-[:IN_SUBCAT]->(c);", {
                "study_id": self.study_id,
                "name": self.name
            }
        )

    def delete(self):
        tx = get_db()
        tx.run(
            "MATCH (s:Study {study_id:{study_id}})-[rel:IN_SUBCAT]->(c:Subcategory {name:{name}}) DELETE rel;", {
                "study_id": self.study_id,
                "name": self.name
            }
        )
