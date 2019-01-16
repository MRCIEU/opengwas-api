from resources._neo4j import get_db


class TraitDescriptionNode:

    def __init__(self, value):
        self.value = value

    def create(self):
        tx = get_db()
        tx.run("MERGE (n:TraitDescription {value:{value}});", {
            "value": self.value
        })

    def delete(self):
        tx = get_db()
        tx.run("MATCH (n:TraitDescription {value:{value}}) "
               "DELETE n;", {
                   "value": self.value
               })

    def get(self):
        tx = get_db()
        results = tx.run(
            "MATCH (n:TraitDescription {value:{value}}) "
            "RETURN n as description;", {
                "value": self.value
            }
        )
        result = results.single()
        return self.__deserialize(result['description'])

    def get_all(self):
        tx = get_db()
        results = tx.run(
            "MATCH (n:TraitDescription) "
            "RETURN n as description;"
        )
        return [self.__deserialize(result['description']) for result in results]

    @staticmethod
    def __deserialize(node):
        return TraitDescriptionNode(node['description'])
