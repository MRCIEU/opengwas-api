
dbConnection = PySQLPool.getNewConnection(host     = "127.0.0.1",
port     = 3307,
user     = "mruser",
passwd   = "TMG_F1WnTL",
db       = "mrbase")

ucscConnection = PySQLPool.getNewConnection(host     = "genome-mysql.cse.ucsc.edu",
user     = "genome",
db       = "hg19")


snps = ["rs10150332", "rs12444979", "rs543874", "rs1558902"]
outcomes = ["1","3","5","6","7","8","9"]
maf_threshold=0.3
palindromes="1"

a = get_proxies_mysql(snps, 0.6, "0", 0.2)

proxy_dat = get_proxies_mysql(snps, rsq, palindromes, maf_threshold)
proxies = [x.get('proxies') for x in [item for sublist in proxy_dat for item in sublist]]
# proxy_query = query_summary_stats(request.args.get('access_token'), joinarray(proxies), joinarray(outcomes))
proxy_query = query_summary_stats("null", joinarray(proxies), joinarray(outcomes))
res = extract_proxies_from_query(outcomes, snps, proxy_dat, proxy_query, maf_threshold)



def test_proxy_alleles(test, maf_threshold):
    exp = test[8]
    pq = {'effect_allele': test[0], 'other_allele': test[1], 'effect_allelel_freq': test[7]}
    pd = {'pallele1': test[2], 'pallele2': test[3], 'tallele1': test[4], 'tallele2': test[5], 'pal': test[6]}
    obs = proxy_alleles(pq, pd, maf_threshold)
    print obs
    return exp == obs


test_proxy_alleles(["A", "G", "A", "G", "T", "C", "0", 0.1, "straight"], 0.3)
test_proxy_alleles(["A", "G", "G", "A", "T", "C", "0", 0.1, "switch"], 0.3)
test_proxy_alleles(["C", "T", "G", "A", "T", "C", "0", 0.1, "straight"], 0.3)
test_proxy_alleles(["C", "T", "A", "G", "T", "C", "0", 0.1, "switch"], 0.3)

test_proxy_alleles(["T", "C", "T", "C", "T", "C", "0", 0.1, "straight"], 0.3)
test_proxy_alleles(["T", "C", "C", "T", "T", "C", "0", 0.1, "switch"], 0.3)
test_proxy_alleles(["T", "C", "A", "G", "T", "C", "0", 0.1, "straight"], 0.3)
test_proxy_alleles(["T", "C", "G", "A", "T", "C", "0", 0.1, "switch"], 0.3)

test_proxy_alleles(["T", None, "T", "C", "T", "C", "0", 0.1, "straight"], 0.3)
test_proxy_alleles(["T", None, "C", "T", "T", "C", "0", 0.1, "switch"], 0.3)
test_proxy_alleles(["T", None, "A", "G", "T", "C", "0", 0.1, "straight"], 0.3)
test_proxy_alleles(["T", None, "G", "A", "T", "C", "0", 0.1, "switch"], 0.3)

test_proxy_alleles(["A", "T", "A", "T", "T", "C", "1", 0.9, "switch"], 0.3)
test_proxy_alleles(["A", "T", "A", "T", "T", "C", "1", 0.1, "straight"], 0.3)
test_proxy_alleles(["A", "T", "T", "A", "T", "C", "1", 0.9, "straight"], 0.3)
test_proxy_alleles(["A", "T", "T", "A", "T", "C", "1", 0.1, "switch"], 0.3)

test_proxy_alleles(["A", None, "A", "T", "T", "C", "1", 0.9, "switch"], 0.3)
test_proxy_alleles(["A", None, "A", "T", "T", "C", "1", 0.1, "straight"], 0.3)
test_proxy_alleles(["A", None, "T", "A", "T", "C", "1", 0.9, "straight"], 0.3)
test_proxy_alleles(["A", None, "T", "A", "T", "C", "1", 0.1, "switch"], 0.3)

test_proxy_alleles(["A", "T", "A", "T", "T", "C", "1", 0.4, "skip"], 0.3)
test_proxy_alleles(["A", "T", "A", "T", "T", "C", "1", 0.4, "skip"], 0.3)
test_proxy_alleles(["A", "T", "T", "A", "T", "C", "1", 0.4, "skip"], 0.3)
test_proxy_alleles(["A", "T", "T", "A", "T", "C", "1", 0.4, "skip"], 0.3)

test_proxy_alleles(["T", "C", "T", "A", "T", "C", "0", 0.1, "skip"], 0.3)
test_proxy_alleles(["T", "C", "C", "A", "T", "C", "0", 0.1, "skip"], 0.3)
test_proxy_alleles(["T", "C", "A", "C", "T", "C", "0", 0.1, "skip"], 0.3)
test_proxy_alleles(["T", "C", "G", "C", "T", "C", "0", 0.1, "skip"], 0.3)




