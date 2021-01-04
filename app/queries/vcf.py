import sqlite3
import pysam


def vcf_location_from_rsid(rsidx_path, rsid):
    """
    Helper function to convert rsID to chromosome and position using [rsidx](https://github.com/bioforensics/rsidx)
    :param rsid: dbsnp indentifier
    :return: res: chromosome
    :return: res: position (1-based)
    """
    if not isinstance(rsid, list):
        rsid = [rsid]
    rsid = [x[2:] for x in rsid]
    sql = "SELECT DISTINCT 'rs' || rsid,chrom,coord FROM rsid_to_coord WHERE rsid IN ({seq})".format(seq=','.join(['?']*len(rsid)))
    with sqlite3.connect(rsidx_path) as dbconn:
        cur = dbconn.cursor()
        cur.execute(sql, rsid)
        res = [{'rsid': x[0], 'chr': x[1], 'start':x[2], 'end':x[2]} for x in cur.fetchall()]
    return res


def parse_item(x):
    a = dict(x.info.items())
    b = {'chrom':x.chrom, 'pos': x.pos, 'id': x.id, 'ref': x.ref, 'alt': x.alts[0]}
    return dict(**a, **b)


def vcf_rsid(rsidlist, vcf, rsidx=None):
    if rsidx is not None:    
        chrpos = vcf_location_from_rsid(rsidx, rsidlist)
        if len(chrpos) > 0:
            return vcf_chrpos(chrpos, vcf)
        else:
            return []
    else:
        res = []
        r = vin.fetch()
        i = 0
        while len(rsidlist) > 0:
            x = next(r)
            if x.id in rsidlist:
                res.append(parse_item(x))
                rsidlist.remove(x.id)
                print(i)
                i = i+1
        return res


def vcf_chrpos(chrpos, vcf):
    vin = pysam.VariantFile(vcf)
    res = []
    for x in chrpos:
        for r in vin.fetch(str(x['chr']), x['start']-1, x['end']):
            res.append(dict(parse_item(r), **x))
    return res
