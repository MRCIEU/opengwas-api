from flask import g
import collections
import gzip
import io
import pickle
import time

from multiprocessing.pool import ThreadPool

from middleware.logger import logger as logger_middleware
from queries.cql_queries import get_permitted_studies
from queries.es import organise_variants, get_proxies_es, extract_proxies_from_query, add_trait_to_result
from queries.variants import snps
from resources.globals import Globals
from resources._oci import OCIObjectStorage


class AssocQueriesByChunks:
    def __init__(self):
        self.oci = OCIObjectStorage()

        self.chunk_size = 10_000_000

    def _convert_sample_size(self, size):
        if size == '':
            return size
        return float(size) if '.' in size else int(size)

    # for each chr, merge the ranges of positions into minimal ranges (https://leetcode.com/problems/merge-intervals/)
    # then work out the groups of chunk to fetch, without knowing which chunks are actually available
    def _merge_pos_ranges(self, pos_tuple_list_by_chr: dict[list[tuple[int, int]]]) -> dict[list[int]]:
        merged_pos_by_chr = collections.defaultdict(list)
        for chr in pos_tuple_list_by_chr.keys():
            pos_tuple_list_by_chr[chr].sort(key=lambda x: x[0])
            for pos_tuple in pos_tuple_list_by_chr[chr]:
                if not merged_pos_by_chr[chr] or merged_pos_by_chr[chr][-1][1] < pos_tuple[0]:
                    merged_pos_by_chr[chr].append(pos_tuple)
                else:
                    merged_pos_by_chr[chr][-1] = (merged_pos_by_chr[chr][-1][0], max(merged_pos_by_chr[chr][-1][1], pos_tuple[1]))
            merged_pos_by_chr[chr].sort(key=lambda x: x[0])
        return merged_pos_by_chr

    # filter out the pos prefixes (chunks) available for the given gwas_id, chr and pos_tuple
    def _filter_chunks_available(self, pos_prefix_indices: dict, gwas_id: str, chr: str, pos_tuple: tuple[int]) -> set:
        chunks_available = set()
        for pos_prefix in range(pos_tuple[0] // self.chunk_size, pos_tuple[1] // self.chunk_size + 1):
            if chr in pos_prefix_indices[gwas_id] and pos_prefix in pos_prefix_indices[gwas_id][chr]:
                chunks_available.add(pos_prefix)
        return chunks_available

    # fetch the associations available for the given gwas_id, chr and pos prefixes (chunks)
    def _fetch_associations_available(self, gwas_id: str, chr: str, pos_prefixes: set) -> dict:
        associations_available = {}
        for pos_prefix in sorted(pos_prefixes):
            with gzip.GzipFile(fileobj=io.BytesIO(self.oci.object_storage_download('data-chunks', f"{gwas_id}/{chr}_{pos_prefix}").data.content), mode='rb') as f:
                associations_available = associations_available | pickle.loads(f.read())
        return associations_available

    # only leave the associations that are within the pos range
    def _trim_and_compose_associations(self, gwasinfo: dict, gwas_id: str, chr: str, associations_available: dict, pos_tuple: tuple[int]) -> list:
        pos_available = list(associations_available.keys())
        if not pos_available or pos_tuple[0] > pos_available[-1] or pos_tuple[1] < pos_available[0]:
            return []

        associations = []
        for pos in pos_available:
            if pos_tuple[0] <= pos <= pos_tuple[1]:
                for assoc in associations_available[pos]:
                    associations.append({
                        'id': gwas_id,
                        'trait': gwasinfo[gwas_id]['trait'],
                        'chr': chr,
                        'position': pos,
                        'rsid': assoc[0],
                        'ea': assoc[1],
                        'nea': assoc[2],
                        'eaf': float(assoc[3]) if assoc[3] != '' else '',
                        'beta': float(assoc[4]) if assoc[4] != '' else '',
                        'se': float(assoc[5]) if assoc[5] != '' else '',
                        'p': float(assoc[6]) if assoc[6] != '' else '',
                        'n': self._convert_sample_size(assoc[7])
                    })
        return associations

    def query_by_multiprocessing(self, pos_prefix_indices: dict, gwasinfo: dict, gwas_ids: list[str], query: list[str]) -> tuple[list, int]:
        def _query(params: tuple):
            gwas_id, chr, pos_tuple = params
            ttask = [time.time()]
            chunks_available = self._filter_chunks_available(pos_prefix_indices, gwas_id, chr, pos_tuple)
            ttask.append(time.time())
            associations_available = self._fetch_associations_available(gwas_id, chr, chunks_available)
            ttask.append(time.time())
            associations = self._trim_and_compose_associations(gwasinfo, gwas_id, chr, associations_available, pos_tuple)
            ttask.append(time.time())
            return associations, ttask, len(chunks_available)

        tquery = [time.time()]
        pos_tuple_list_by_chr = collections.defaultdict(list)
        for q in query:
            chr, pos = q.split(':')
            pos_start, pos_end = pos.split('-') if '-' in pos else (pos, pos)
            pos_tuple_list_by_chr[chr].append((int(pos_start), int(pos_end)))
        merged_pos_by_chr = self._merge_pos_ranges(pos_tuple_list_by_chr)

        tasks = []
        for gwas_id in gwas_ids:
            for chr in merged_pos_by_chr:
                for pos_tuple in merged_pos_by_chr[chr]:
                    tasks.append((gwas_id, chr, pos_tuple))

        n_proc = max(len(tasks), Globals.ASSOC_QUERY_BY_CHUNKS_MAX_N_THREADS)

        tquery.append(time.time())

        with ThreadPool(n_proc) as pool:
            async_instance = pool.map_async(_query, tasks)
            tquery.append(time.time())
            try:
                results = []
                times_by_steps = [[], [], []]
                n_chunks_accessed = 0
                outcome = async_instance.get()
                tquery.append(time.time())
                for associations, time_by_step_of_query, chunks_available in outcome:
                    results.extend(associations)
                    for step in [0, 1, 2]:
                        times_by_steps[step].append(time_by_step_of_query[step + 1] - time_by_step_of_query[step])
                    n_chunks_accessed += chunks_available
                tquery.append(time.time())

                tquery = [round((tquery[i + 1] - tquery[i]) * 1000, 2) for i in range(len(tquery) - 1)]
                tquery.extend([int(sum(times_of_step) * 1000 / max(len(times_of_step), 1)) for times_of_step in times_by_steps])
                logger_middleware.log_info(g.user['uuid'], 'assoc_query_by_chunks', {'n_tasks': len(tasks)}, tquery)
            except Exception as e:
                print(str(e))
                raise e

        return results, n_chunks_accessed


def get_assoc_chunked(user_email, variants: list, ids: list, proxies, r2=None, align_alleles=None, palindromes=None, maf_threshold=None, study_data=None):
    """
    Adapted from queries.es.get_assoc()
    """
    variants = organise_variants(variants)
    if not study_data:  # Need to get metadata and keep those permitted, otherwise take the study_data provided as permitted
        study_data = get_permitted_studies(user_email, ids)
        id_access = list(study_data.keys())
        if len(id_access) == 0:
            return [], 0
        for id in ids:
            if id not in id_access:
                ids.remove(id)

    rsid = variants['rsid']
    chrpos = variants['chrpos']
    cprange = variants['cprange']

    chunked_queries = AssocQueriesByChunks()

    query = set()
    result = []
    n_chunks_accessed_total = 0
    if len(rsid) > 0:
        if proxies == 0:
            total, docs = snps(rsid)
            query.update([f"{doc['_source']['CHR']}:{doc['_source']['POS']}" for doc in docs])
        else:
            proxy_dat = get_proxies_es(rsid, r2, palindromes, maf_threshold)
            rsid_proxies = list(set([x.get('proxies') for x in [item for sublist in proxy_dat for item in sublist]]))
            total, docs = snps(rsid_proxies)
            assoc_proxied, n_chunks_accessed = chunked_queries.query_by_multiprocessing(Globals.gwas_pos_prefix_indices, study_data, ids, [f"{doc['_source']['CHR']}:{doc['_source']['POS']}" for doc in docs])
            # Need to fix this (which?)
            if assoc_proxied != '[]':
                result += extract_proxies_from_query(ids, rsid, proxy_dat, assoc_proxied, maf_threshold, align_alleles)
            n_chunks_accessed_total += n_chunks_accessed

    if len(chrpos) > 0:
        query.update([cp['orig'] for cp in chrpos])

    if len(cprange) > 0:
        query.update([cp['orig'] for cp in cprange])

    assoc, n_chunks_accessed = chunked_queries.query_by_multiprocessing(Globals.gwas_pos_prefix_indices, study_data, ids, list(query))
    result += assoc
    n_chunks_accessed_total += n_chunks_accessed

    result = sorted(result, key=lambda x: x['position'])
    result = add_trait_to_result(result, study_data)
    return result, n_chunks_accessed_total
