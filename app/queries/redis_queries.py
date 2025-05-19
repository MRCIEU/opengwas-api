from collections import defaultdict
import jsonpickle

from resources.redis import Redis
from resources.redis_proxy import RedisProxy


class RedisQueries:
    def __init__(self, db_name, provider='redis'):
        if provider == 'redis':
            self.r = Redis().conn[db_name]
        elif provider in ['ieu-db-proxy', 'ieu-ssd-proxy']:
            self.r = RedisProxy(provider, db_name)
        return

    def _strip_b_in_keys(self, d: dict):
        """
        Remove the "b'" prefix and the "'" suffix in literal string (complication of jsonpickle)
        :param d:
        :return:
        """
        return {k[2:-1]: v for k, v in d.items()}

    def publish_log(self, channel, data):
        """
        :param channel:
        :param data:
        :return: number of subscribers
        """
        return self.r.publish(channel, data)

    def add_log(self, key: str, score: float, member: str):
        return self.r.zadd(name=key, mapping={member: score})

    def count_online_users(self) -> int:
        result = 0
        for _ in self.r.scan_iter(match="*allowance_by_user_tier*", count=1000):
            result += 1
        return result

    def add_tasks(self, tasks: list):
        return self.r.query([{
            'cmd': 'sadd',
            'args': {
                "name": 'tasks_pending',
                "values": tasks
            }
        }])[0]

    # def add_phewas_tasks(self, tasks: list):
    #     return self.r.query([{
    #         'cmd': 'sadd',
    #         'args': {
    #             "name": 'phewas_pending',
    #             "values": tasks
    #         }
    #     }])[0]

    def get_completed_tasks(self):
        return self.r.query([{
            'cmd': 'zrange',
            'args': {
                "name": 'tasks_completed',
                "start": 0,
                "end": -1
            }
        }])[0]

    def get_gwas_pos_prefix_indices(self):
        r = self.r.query([{
            'cmd': 'hgetall',
            'args': {
                "name": 'gwas_pos_prefix_indices'
            }
        }], get_raw_response=True)[0]
        return self._strip_b_in_keys(jsonpickle.decode(r))

    # def get_completed_phewas_tasks(self):
    #     return self.r.query([{
    #         'cmd': 'zrange',
    #         'args': {
    #             "name": 'phewas_completed',
    #             "start": 0,
    #             "end": -1
    #         }
    #     }])[0]

    def get_cpalleles_of_chr_pos(self, chr_pos: set[tuple]) -> set:
        """
        Get chr, pos, alleles combinations from Redis, using chrpos or cprange.
        :param chr_pos: list of (chr(str), pos_start, pos_end) tuples e.g. [('1', 12345, 12345), ('1', 12345, 12400)]
        :return: set of cpalleles e.g. {'1:12345:G:C', '1:12398:AT:G'}
        """
        chr_pos = list(chr_pos)
        cpalleles = set()
        cmds = []
        for cp in chr_pos:
            cmds.append({
                'cmd': 'zrange',
                'args': {
                    "name": cp[0],
                    "start": cp[1],
                    "end": cp[2],
                    "byscore": "True"
                }
            })
        for seq, pos_alleles_of_chr_pos in enumerate(self.r.query(cmds)):
            for pos_alleles in pos_alleles_of_chr_pos:
                cpalleles.add(chr_pos[seq][0] + ':' + pos_alleles)
        return cpalleles

    def get_gwas_n_ids_of_cpalleles_and_pval(self, cpalleles: set, pval: float) -> dict[set]:
        """
        Get Neo4j elementId(n) from Redis, using cpalleles and pval
        :param cpalleles: set of cpalleles e.g. {'1:12345:G:C', '1:12398:AT:G'}
        :param pval:
        :return:
        """
        gwas_n_ids = defaultdict(set)
        cmds = []
        cpalleles = list(cpalleles)
        for chr_pos_alleles in cpalleles:
            cmds.append({
                'cmd': 'zrange',
                'args': {
                    "name": chr_pos_alleles,
                    "start": 0,
                    "end": '(' + str(pval),
                    "byscore": "True"
                }
            })
        for seq, gwas_n_ids_of_chr_pos_alleles in enumerate(self.r.query(cmds)):
            for gwas_n_id in gwas_n_ids_of_chr_pos_alleles:
                gwas_n_ids[int(gwas_n_id)].add(':'.join(cpalleles[seq].split(':')[:2]))
        return gwas_n_ids

    def save_cache(self, key: str, field: str, value: str):
        return self.r.hset(name=key, key=field, value=value)

    def get_cache(self, key: str, field: str):
        return self.r.hget(name=key, key=field)

    def delete_cache(self, key: str, field: str):
        return self.r.hdel(key, field)

    def get_cache_all(self, key: str):
        return self.r.hgetall(name=key)
