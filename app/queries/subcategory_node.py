from resources._neo4j import get_db


class SubcategoryNode:

    def __init__(self, name):
        self.name = str(name)

    def create(self):
        tx = get_db()
        tx.run("MERGE (n:Subcategory {name:{name}})", {
            "name": self.name
        })

    def delete(self):
        tx = get_db()
        tx.run("MATCH (n:Subcategory {name:{name}}) "
               "DELETE n;", {
                   "name": self.name
               })

    def get(self):
        tx = get_db()
        results = tx.run(
            "MATCH (n:Subcategory {name:{name}}) "
            "RETURN n as subcategory;", {
                "name": self.name
            }
        )
        result = results.single()
        return self.__deserialize(result['subcategory'])

    def get_all(self):
        tx = get_db()
        results = tx.run(
            "MATCH (n:Subcategory) "
            "RETURN n as subcategory;"
        )
        return [self.__deserialize(result['subcategory']) for result in results]

    @staticmethod
    def __deserialize(node):
        n = SubcategoryNode(node['subcategory'])
        return n
