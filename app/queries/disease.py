from resources._neo4j import get_db


class Disease:

    def __init__(self, did, name):
        self.did = int(did)
        self.name = str(name)

    def create(self):
        tx = get_db()
        tx.run("MERGE (n:Disease {did:{did}}) "
               "SET n.name={name}", {
                   "name": self.name
               })

    def delete(self):
        tx = get_db()
        tx.run("MATCH (n:Disease {did:{did}}) "
               "DELETE n;", {
                   "name": self.name
               })

    def get(self):
        tx = get_db()
        results = tx.run(
            "MATCH (d:Disease {name:{name}}) "
            "RETURN n as disease;", {
                "gid": self.did
            }
        )
        result = results.single()
        return self.__deserialize(result['group'])

    def get_all(self):
        tx = get_db()
        results = tx.run(
            "MATCH (d:Disease) RETURN n as disease;"
        )
        return [self.__deserialize(result['disease']) for result in results]

    @staticmethod
    def __deserialize(node):
        n = Disease(node['did'], node['name'])
        return n
