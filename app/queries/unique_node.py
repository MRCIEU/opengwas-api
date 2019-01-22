from resources._neo4j import get_db


class UniqueNode:

    def __init__(self, uid):
        self._uid = uid

    @property
    def uid(self):
        return self._uid

    @uid.setter
    def uid(self, value):
        if value is None:
            raise ValueError("UID cannot be null.")
        self._uid = value

    def get_props(self):
        class_items = self.__class__.__dict__.items()
        d = dict((k, getattr(self, k))
                 for k, v in class_items
                 if isinstance(v, property))
        d['uid'] = self.uid
        return d

    # TODO get id from props
    def create(self):
        tx = get_db()
        tx.run(
            "MERGE (n:" + str(self.__class__.__name__) + " {uid:{uid}}) SET n = {params};", uid=self.uid,
            params=self.get_props()
        )

    @classmethod
    def delete(cls, uid):
        tx = get_db()
        tx.run(
            "MATCH (n:" + str(cls.__name__) + " {uid:{uid}}) OPTIONAL MATCH (n)-[r]-() DELETE n, r;", uid=uid
        )

    @classmethod
    def get(cls, uid):
        tx = get_db()
        results = tx.run(
            "MATCH (n:" + str(cls.__name__) + " {uid:{uid}}) RETURN n;", uid=uid
        )
        result = results.single()

        if result is None:
            raise LookupError("Node does not exist for: {}".format(uid))

        return result['n']

    @classmethod
    def set_constraint(cls):
        tx = get_db()
        tx.run(
            "CREATE CONSTRAINT ON (n:" + str(cls.__name__) + ") ASSERT n.uid IS UNIQUE;"
        )

    @classmethod
    def check_constraint(cls):
        labels = set()
        tx = get_db()
        results = tx.run(
            "CALL db.indexes();"
        )
        for result in results:
            if 'uid' in result['properties']:
                labels.add(result['label'])
        return str(cls.__name__) in labels

    # TODO -- does not work correctly
    @classmethod
    def deserialize(cls, dat):
        return eval(str(cls.__name__))(**dat)
