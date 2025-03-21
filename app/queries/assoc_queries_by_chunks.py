import collections
import gzip
import os
import pickle
import shutil
import uuid

from multiprocessing.pool import ThreadPool

from queries.cql_queries import get_permitted_studies
from queries.es import organise_variants, get_proxies_es, extract_proxies_from_query, add_trait_to_result
from queries.variants import snps
from resources.globals import Globals
from resources._oci import OCI


# TODO: https://stackoverflow.com/questions/64514398/python-multiprocessing-within-flask-request-with-gunicorn-nginx


class AssocQueriesByChunks:
    def __init__(self):
        self.oci = OCI()

        self.temp_dir = f"{Globals.TMP_FOLDER}/{uuid.uuid4()}"
        os.makedirs(self.temp_dir, exist_ok=True)

        self.chunk_size = 10_000_000

    def __del__(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

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
            chunk_path = f"{self.temp_dir}/{gwas_id}/{chr}_{pos_prefix}"
            local_file_valid = os.path.exists(chunk_path) and os.path.getsize(chunk_path) > 0
            try:
                with gzip.open(chunk_path, 'rb') as f:
                    associations_available = associations_available | pickle.load(f)
            except Exception as e:
                local_file_valid = False
            if not local_file_valid:
                os.makedirs(f"{self.temp_dir}/{gwas_id}", exist_ok=True)
                with open(chunk_path, 'wb+') as f:
                    f.write(self.oci.object_storage_download('data-chunks', f"{gwas_id}/{chr}_{pos_prefix}").data.content)
                with gzip.open(chunk_path, 'rb') as f:
                    associations_available = associations_available | pickle.load(f)
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

    def query_by_multiprocessing(self, pos_prefix_indices: dict, gwasinfo: dict, gwas_ids: list[str], query: list[str]) -> list:
        def _query(t: tuple):
            gwas_id, chr, pos_tuple = t
            chunks_available = self._filter_chunks_available(pos_prefix_indices, gwas_id, chr, pos_tuple)
            associations_available = self._fetch_associations_available(gwas_id, chr, chunks_available)
            associations = self._trim_and_compose_associations(gwasinfo, gwas_id, chr, associations_available, pos_tuple)
            return associations

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

        with ThreadPool(n_proc) as pool:
            async_instance = pool.map_async(_query, tasks)
            try:
                results = []
                for r in async_instance.get():
                    results.extend(r)
            except Exception as e:
                print(str(e))
                raise e

        return results


def get_assoc_chunked(user_email, variants: list, ids: list, proxies, r2, align_alleles, palindromes, maf_threshold):
    """
    Adapted from queries.es.get_assoc()
    """
    variants = organise_variants(variants)
    study_data = get_permitted_studies(user_email, ids)
    id_access = list(study_data.keys())
    if len(id_access) == 0:
        return []
    for id in ids:
        if id not in id_access:
            ids.remove(id)

    rsid = variants['rsid']
    chrpos = variants['chrpos']
    cprange = variants['cprange']

    chunked_queries = AssocQueriesByChunks()

    query = set()
    result = []
    if len(rsid) > 0:
        if proxies == 0:
            total, docs = snps(rsid)
            query.update([f"{doc['_source']['CHROM']}:{doc['_source']['POS']}" for doc in docs])
        else:
            proxy_dat = get_proxies_es(rsid, r2, palindromes, maf_threshold)
            rsid_proxies = list(set([x.get('proxies') for x in [item for sublist in proxy_dat for item in sublist]]))
            total, docs = snps(rsid_proxies)
            assoc_proxied = chunked_queries.query_by_multiprocessing(Globals.gwas_pos_prefix_indices, study_data, ids, [f"{doc['_source']['CHROM']}:{doc['_source']['POS']}" for doc in docs])
            # Need to fix this (which?)
            if assoc_proxied != '[]':
                result += extract_proxies_from_query(ids, rsid, proxy_dat, assoc_proxied, maf_threshold, align_alleles)

    if len(chrpos) > 0:
        query.update([cp['orig'] for cp in chrpos])

    if len(cprange) > 0:
        query.update([cp['orig'] for cp in cprange])

    result += chunked_queries.query_by_multiprocessing(Globals.gwas_pos_prefix_indices, study_data, ids, list(query))

    result = sorted(result, key=lambda x: x['position'])
    result = add_trait_to_result(result, study_data)
    return result
