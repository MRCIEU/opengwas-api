from resources._neo4j import get_db


class HasTraitDescRel:

    def __init__(self, study_id, trait_description):
        self.study_id = str(study_id)
        self.trait_description = str(trait_description)

    def create(self):
        tx = get_db()
        tx.run(
            "MATCH (s:Study {study_id:{study_id}}) "
            "MATCH (d:TraitDescription {value:{value}}) "
            "MERGE (s)-[:HAS_TRAIT_DESC]->(d);", {
                "study_id": self.study_id,
                "value": self.trait_description
            }
        )

    def delete(self):
        tx = get_db()
        tx.run(
            "MATCH (s:Study {study_id:{study_id}})-[rel:HAS_TRAIT_DESC]->(d:TraitDescription {value:{value}}) DELETE rel;",
            {
                "study_id": self.study_id,
                "value": self.trait_description
            }
        )
