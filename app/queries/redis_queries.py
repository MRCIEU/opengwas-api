from resources.redis import Redis


class RedisQueries:
    def __init__(self, db_name):
        self.r = Redis().conn[db_name]
        return

    def publish_log(self, channel, data):
        """
        :param channel:
        :param data:
        :return: number of subscribers
        """
        return self.r.publish(channel, data)

    def count_online_users(self):
        result = 0
        for _ in self.r.scan_iter(match="*allowance_by_user_source*", count=1000):
            result += 1
        return result

    def add_phewas_tasks(self, tasks: list):
        return self.r.rpush('pending', *tasks)

    def get_completed_phewas_tasks(self):
        return self.r.zrange('completed', 0, -1)
