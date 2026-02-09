from collections import defaultdict
from typing import Literal

from queries.mysql_queries import MySQLQueries

def get_proxies_from_mysql(
        population: Literal['proxies_afr', 'proxies_amr', 'proxies_eas', 'proxies_eur', 'proxies_sas'],
        target_snps: list[str], r2: float, palindromic: Literal[0, 1], maf_threshold: float
) -> dict[str, list]:
    mysql_queries = MySQLQueries()
    proxies_raw = mysql_queries.get_proxies(f"proxies_{population.lower()}", target_snps, r2, palindromic, maf_threshold)
    result = defaultdict(list)
    for p in proxies_raw:
        if p['target_column'] == 'a':
            result[p['rsid_a']].append({
                'target': p['rsid_a'],
                'proxy': p['rsid_b'],
                'target_maf': p['maf_a'],
                'proxy_maf': p['maf_b'],
                'r2': p['r2'],
                'distance': p['distance'],
                'target_a1': p['allele_a1'],
                'target_a2': p['allele_a2'],
                'proxy_a1': p['allele_b1'],
                'proxy_a2': p['allele_b2'],
                'palindromic': p['palindromic'],
            })
        else:
            result[p['rsid_b']].append({
                'target': p['rsid_b'],
                'proxy': p['rsid_a'],
                'target_maf': p['maf_b'],
                'proxy_maf': p['maf_a'],
                'r2': p['r2'],
                'distance': p['distance'],
                'target_a1': p['allele_b1'],
                'target_a2': p['allele_b2'],
                'proxy_a1': p['allele_a1'],
                'proxy_a2': p['allele_a2'],
                'palindromic': p['palindromic'],
            })
    return dict(result)


def allele_check(x):
    if x is None:
        return x
    x = x.upper()
    return x if x in ["A", "T", "G", "C"] else None


def flip(x):
    return {
        "A": "T",
        "T": "A",
        "G": "C",
        "C": "G",
    }.get(x)


def proxy_alleles(association, proxy, maf_threshold):
    a1 = allele_check(association.get('ea'))
    a2 = allele_check(association.get('nea'))
    p_a1 = proxy.get('proxy_a1')
    p_a2 = proxy.get('proxy_a2')
    if a1 is None:
        return "no_allele"
    if proxy.get('palindromic') == 0:
        if (a1 == p_a1 and a2 == p_a2) or (a1 == flip(p_a1) and a2 == flip(p_a2)):
            return "straight"
        if (a1 == p_a2 and a2 == p_a1) or (a1 == flip(p_a2) and a2 == flip(p_a1)):
            return "switch"
        if (a1 == p_a1 and a2 is None) or (a1 == flip(p_a1) and a2 is None):
            return "straight"
        if (a1 == p_a2 and a2 is None) or (a1 == flip(p_a2) and a2 is None):
            return "switch"
        return "skip"
    else:
        eaf = association.get('eaf')
        if not eaf:
            return "skip"
        if eaf < maf_threshold:
            if (a1 == p_a1 and a2 == p_a2) or (a1 == p_a1 and a2 is None):
                return "straight"
            if (a1 == flip(p_a1) and a2 == flip(p_a2)) or (a1 == flip(p_a1) and a2 is None):
                return "switch"
        if eaf > 1 - maf_threshold:
            if (a1 == p_a1 and a2 == p_a2) or (a1 == p_a1 and a2 is None):
                return "switch"
            if (a1 == flip(p_a1) and a2 == flip(p_a2)) or (a1 == flip(p_a1) and a2 is None):
                return "straight"
        return "skip"


def annotate_associations(gwas_ids: list[str], rsids: list[str], proxies: dict[str, list], associations: list, maf_threshold: float, align_alleles: Literal[0, 1]) -> list[dict]:
    result = []
    for gwas_id in gwas_ids:  # Each gwas_id in the query
        for rsid in rsids:  # Each target rsid in the query
            added = False  # Ensuring no more than one association is added for each target rsid in each gwas_id
            # Priority as below
            # - Direct hit (target is available)
            # - The first proxy with straight alignment
            # - The first proxy with switch alignment
            # - The first proxy without alignment
            # Note that the order of proxies should have been ensured by MySQL asc(distance) already
            for proxy_of_the_target in proxies[rsid]:  # Each proxy (dict) in all the proxies of a target
                if added:
                    break
                for a in associations:
                    # Note that each association here is for the proxy, so need to annotate it with the target info (provided by the user)
                    # When: association belongs to the dataset in the query, and its rsid is in the query
                    if a['rsid'] == proxy_of_the_target['proxy'] and a['id'] == gwas_id:
                        r = a.copy()
                        r.update({
                            'target_snp': rsid,
                            'proxy_snp': proxy_of_the_target['proxy'],
                        })
                        if a['rsid'] == rsid:
                            r.update({
                                'proxy': False,
                                'target_a1': None,
                                'target_a2': None,
                                'proxy_a1': None,
                                'proxy_a2': None,
                            })
                            result.append(r)
                            added = True
                        else:
                            if align_alleles == 1:
                                match proxy_alleles(a, proxy_of_the_target, maf_threshold):
                                    case 'straight':
                                        r.update({
                                            'proxy': True,
                                            'ea': proxy_of_the_target['target_a1'],
                                            'nea': proxy_of_the_target['target_a2'],
                                            'target_a1': proxy_of_the_target['target_a1'],
                                            'target_a2': proxy_of_the_target['target_a2'],
                                            'proxy_a1': proxy_of_the_target['proxy_a1'],
                                            'proxy_a2': proxy_of_the_target['proxy_a2'],
                                            'rsid': rsid,
                                        })
                                        result.append(r)
                                        added = True
                                    case 'switch':
                                        r.update({
                                            'proxy': True,
                                            'ea': proxy_of_the_target['target_a2'],
                                            'nea': proxy_of_the_target['target_a1'],
                                            'target_a1': proxy_of_the_target['target_a1'],
                                            'target_a2': proxy_of_the_target['target_a2'],
                                            'proxy_a1': proxy_of_the_target['proxy_a1'],
                                            'proxy_a2': proxy_of_the_target['proxy_a2'],
                                            'rsid': rsid,
                                        })
                                        result.append(r)
                                        added = True
                                    case 'skip':
                                        pass
                                    case 'no_allele':
                                        pass
                            else:
                                r.update({
                                    'proxy': True,
                                    'target_a1': proxy_of_the_target['target_a1'],
                                    'target_a2': proxy_of_the_target['target_a2'],
                                    'proxy_a1': proxy_of_the_target['proxy_a1'],
                                    'proxy_a2': proxy_of_the_target['proxy_a2'],
                                    'rsid': rsid,
                                })
                                result.append(r)
                                added = True
    return result



