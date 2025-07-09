from flask import g
import math

def compare_results(r0, r1):
    r0fset = {frozenset(a.items()) for a in r0}
    r1fset = {frozenset(a.items()) for a in r1}

    r0uniq = r0fset - r1fset
    r1uniq = r1fset - r0fset

    anomalies = []

    r0uniq = [{a[0]: a[1] for a in fset} for fset in r0uniq]
    r0uniq_dict = {f"{a['id']}_{a['chr']}_{a['position']}_{a['rsid']}_{a['ea']}_{a['nea']}": a for a in r0uniq}
    if len(r0uniq_dict) != len(r0uniq):
        anomalies.append(['DUPLICATE_ID', 'r0'])

    r1uniq = [{a[0]: a[1] for a in fset} for fset in r1uniq]
    r1uniq_dict = {f"{a['id']}_{a['chr']}_{a['position']}_{a['rsid']}_{a['ea']}_{a['nea']}": a for a in r1uniq}
    if len(r1uniq_dict) != len(r1uniq):
        anomalies.append(['DUPLICATE_ID', 'r1'])

    print(len(r0uniq_dict), len(r1uniq_dict))

    def _compare(dict1, dict2):
        for id in dict1.keys():
            if id not in dict2:
                anomalies.append(['MISSING_ID', id])
            elif dict1[id] != dict2[id]:
                diff_keys = {k for k in dict1[id] if dict1[id][k] != dict2[id][k]}
                if not (
                    (diff_keys == {'n'} and int(float('0' + str(dict1[id]['n']))) == int(float('0' + str(dict2[id]['n'])))) or
                    (diff_keys == {'beta', 'eaf'} and
                        math.isclose(float(dict1[id]['beta']) * -1, float(dict2[id]['beta']), rel_tol=1e-6) and
                        math.isclose(float(dict1[id]['eaf']) + float(dict2[id]['eaf']), 1.000000, rel_tol=1e-6)
                    )
                ):
                    anomalies.append(['DIFF_IN_VALUE', dict1[id], dict2[id], list(diff_keys)])

    _compare(r0uniq_dict, r1uniq_dict)
    _compare(r1uniq_dict, r0uniq_dict)

    return anomalies

# Only applies to data files derived from VCF
def fix_legacy_value_errors(results: list):
    for i in range(len(results)):
        # Fix beta and eaf for ukb-e
        if results[i]['id'].startswith('ukb-e'):
            if not (g.client['source'] == 'R' and g.client['version'] == 'TwoSampleMR'):
                # For R/TwoSampleMR (actually ieugwasr <= 1.0.4), beta will be fixed by the client
                # Since the value in results is correct, we need to flip it here so that it can be "fixed" by the client
                # https://github.com/MRCIEU/ieugwasr/blob/4224670b09fa5dddfb2a24af514a0629edd1de38/R/query.R#L391
                results[i]['beta'] *= -1
            results[i]['eaf'] = 1 - results[i]['eaf']
    return results
