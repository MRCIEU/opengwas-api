from resources._neo4j import get_db


# TODO parameter validation
class User:

    def __init__(self, uid):
        self.uid = str(uid)

    def create(self):
        tx = get_db()
        tx.run("MERGE (n:User {uid:{uid}});")

    def get(self):
        tx = get_db()
        results = tx.run(
            "MATCH (n:User {uid:{uid}}) "
            "RETURN n as user;", {
                "uid": self.uid
            }
        )
        result = results.single()
        return self.__deserialize(result['user'])

    @staticmethod
    def __deserialize(node):
        n = User(node['uid'])
        for key in node['uid']:
            setattr(n, key, node['uid'][key])
        return n
