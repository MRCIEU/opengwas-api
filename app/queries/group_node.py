from resources._neo4j import get_db


# TODO parameter validation
class GroupNode:

    def __init__(self, gid, name=None):
        self.gid = int(gid)
        self.name = name

    def create(self):
        tx = get_db()
        tx.run("MERGE (n:Group {gid:{gid}}) "
               "SET n.name={name}", {
                   "name": self.name
               })

    def delete(self):
        tx = get_db()
        tx.run("MATCH (n:Group {gid:{gid}}) "
               "DELETE n;", {
                   "name": self.name
               })

    def get(self):
        tx = get_db()
        results = tx.run(
            "MATCH (n:Group {gid:{gid}}) "
            "RETURN n as group;", {
                "gid": self.gid
            }
        )
        result = results.single()
        return self.__deserialize(result['group'])

    @staticmethod
    def __deserialize(node):
        n = GroupNode(node['gid'])
        for key in node['gid']:
            setattr(n, key, node['gid'][key])
        return n
