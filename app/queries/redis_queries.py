from collections import defaultdict

from resources.redis import Redis
from resources.redis_proxy import RedisProxy


class RedisQueries:
    def __init__(self, db_name, provider='redis'):
        if provider == 'redis':
            self.r = Redis().conn[db_name]
        elif provider in ['ieu-db-proxy', 'ieu-ssd-proxy']:
            self.r = RedisProxy(provider, db_name)
        return

    def publish_log(self, channel, data):
        """
        :param channel:
        :param data:
        :return: number of subscribers
        """
        return self.r.publish(channel, data)

    def count_online_users(self) -> int:
        result = 0
        for _ in self.r.scan_iter(match="*allowance_by_user_tier*", count=1000):
            result += 1
        return result

    def add_gwas_tasks(self, tasks: list):
        return self.r.query(['SADD', 'gwas_pending'] + tasks)

    def add_phewas_tasks(self, tasks: list):
        return self.r.query(['SADD', 'phewas_pending'] + tasks)

    def get_completed_gwas_tasks(self):
        return self.r.query(['ZRANGE', 'gwas_completed', 0, -1])['ZRANGE']

    def get_completed_phewas_tasks(self):
        return self.r.query(['ZRANGE', 'phewas_completed', 0, -1])['ZRANGE']

    def get_cpalleles_of_chr_pos(self, chr_pos: set[tuple]) -> set:
        """
        Get chr, pos, alleles combinations from Redis, using chrpos or cprange.
        :param chr_pos: list of (chr(str), pos_start, pos_end) tuples e.g. [('1', 12345, 12345), ('1', 12345, 12400)]
        :return: set of cpalleles e.g. {'1:12345:G:C', '1:12398:AT:G'}
        """
        # When using redis-py, which supports native pipelining
        # chr_pos = list(chr_pos)  # Should be sequential as pipeline will be used
        # pipe = self.r.pipeline()
        # chrs = []
        # for cp in chr_pos:
        #     pipe.zrange(cp[0], start=cp[1], end=cp[2], byscore=True)
        #     chrs.append(cp[0])
        # results = pipe.execute()
        # cpalleles = set()
        # for i in range(len(chrs)):
        #     for pos_alleles in results[i]:
        #         cpalleles.add(chrs[i] + ':' + pos_alleles.decode('ascii'))
        # return cpalleles

        # When using redis proxy, where pipelining is implemented at proxy level
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

    def get_doc_ids_of_cpalleles_and_pval(self, cpalleles: set, pval: float) -> dict[set]:
        """
        Get Elasticsearch document IDs from Redis, using cpalleles and pval
        :param cpalleles: set of cpalleles e.g. {'1:12345:G:C', '1:12398:AT:G'}
        :param pval:
        :return:
        """
        # When using redis-py, which supports native pipelining
        # pipe = self.r.pipeline()
        # for chr_pos_alleles in cpalleles:
        #     pipe.zrange(chr_pos_alleles, start=0, end=pval, byscore=True)
        # results = pipe.execute()
        # doc_ids = defaultdict(set)
        # for doc_ids_of_cpalleles in results:
        #     for doc_id in doc_ids_of_cpalleles:
        #         index_and_doc_id = doc_id.decode('ascii').split(':')
        #         doc_ids[index_and_doc_id[0]].add(index_and_doc_id[1])
        # return doc_ids

        # When using redis proxy, where pipelining is implemented at proxy level
        doc_ids = defaultdict(set)
        cmds = []
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
        for seq, doc_ids_of_chr_pos_alleles in enumerate(self.r.query(cmds)):
            for doc_id in doc_ids_of_chr_pos_alleles:
                index_and_doc_id = doc_id.split(':')
                doc_ids[index_and_doc_id[0]].add(index_and_doc_id[1])
        return doc_ids

    def save_cache(self, key: str, field: str, value: str):
        return self.r.hset(name=key, key=field, value=value)

    def get_cache(self, key: str, field: str):
        return self.r.hget(name=key, key=field)

    def delete_cache(self, key: str, field: str):
        return self.r.hdel(key, field)

    def get_cache_all(self, key: str):
        return self.r.hgetall(name=key)
