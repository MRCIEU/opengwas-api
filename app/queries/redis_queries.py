from collections import defaultdict

from resources.redis import Redis
from resources.webdis import Webdis


class RedisQueries:
    def __init__(self, db_name, provider='redis'):
        if provider == 'redis':
            self.r = Redis().conn[db_name]
        elif provider == 'webdis':
            self.r = Webdis(db_name)
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
        for _ in self.r.scan_iter(match="*allowance_by_user_source*", count=1000):
            result += 1
        return result

    def add_phewas_tasks(self, tasks: list):
        return self.r.rpush('pending', *tasks)

    def get_completed_phewas_tasks(self):
        return self.r.zrange('completed', 0, -1)

    def get_cpalleles_of_chr_pos(self, chr_pos: set[tuple]) -> set:
        """
        Get chr, pos, alleles combinations from Redis, using chrpos or cprange.
        :param chr_pos: list of (chr(str), pos_start, pos_end) tuples e.g. [('1', 12345, 12345), ('1', 12345, 12400)]
        :return: set of cpalleles e.g. {'1:12345:G:C', '1:12398:AT:G'}
        """
        # When using redis-py, which supports pipelining
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

        # When using webdis, where pipelining is unavailable
        cpalleles = set()
        for cp in chr_pos:
            for pos_alleles in self.r.query(['ZRANGE', cp[0], cp[1], cp[2], 'BYSCORE'])['ZRANGE']:
                cpalleles.add(cp[0] + ':' + pos_alleles)
        return cpalleles

    def get_doc_ids_of_cpalleles_and_pval(self, cpalleles: set, pval: float) -> dict[set]:
        """
        Get Elasticsearch document IDs from Redis, using cpalleles and pval
        :param cpalleles: set of cpalleles e.g. {'1:12345:G:C', '1:12398:AT:G'}
        :param pval:
        :return:
        """
        # When using redis-py, which supports pipelining
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

        # When using webdis, where pipelining is unavailable
        doc_ids = defaultdict(set)
        for chr_pos_alleles in cpalleles:
            for doc_id in self.r.query(['ZRANGE', chr_pos_alleles, 0, '(' + str(pval), 'BYSCORE'])['ZRANGE']:
                index_and_doc_id = doc_id.split(':')
                doc_ids[index_and_doc_id[0]].add(index_and_doc_id[1])
        return doc_ids
