import time
from _logger import *

def extract_proxies_from_query(outcomes, snps, proxy_dat, proxy_query, maf_threshold, align_alleles):
	logger2.debug("entering extract_proxies_from_query")
	start = time.time()
	matched_proxies = []
	proxy_query_copy = [a.get('name') for a in proxy_query]
	for i in range(len(outcomes)):
		logger2.debug("matching proxies to query snps for " + str(i))
		for j in range(len(snps)):
			#logger.info(str(j)+' '+snps[j])
			flag=0
			for k in range(len(proxy_dat[j])):
				#logger.info(str(k)+' '+str(proxy_dat[j][k]))
				if flag == 1:
					#logger.info(flag)
					break
				for l in range(len(proxy_query)):
					if (proxy_query[l].get('name') == proxy_dat[j][k].get('proxies')) and (str(proxy_query[l].get('id')) == outcomes[i]):
						#logger.info(proxy_query[l].get('name'))
						y = dict(proxy_query[l])
						y['target_snp'] = snps[j]
						y['proxy_snp'] = proxy_query[l].get('name')
						#logger.info(y['target_snp']+' : '+y['proxy_snp'])
						if(snps[j] == proxy_query[l].get('name')):
							y['proxy'] = False
							y['target_a1'] = None
							y['target_a2'] = None
							y['proxy_a1'] = None
							y['proxy_a2'] = None
							matched_proxies.append(y.copy())
							flag = 1
						else:
							if align_alleles == "1":
								al = proxy_alleles(proxy_query[l], proxy_dat[j][k], maf_threshold)
								logger2.debug(al)
								if al == "straight":
									y['proxy'] = True
									y['effect_allele'] = proxy_dat[j][k].get('tallele1')
									y['other_allele'] = proxy_dat[j][k].get('tallele2')
									y['target_a1'] = proxy_dat[j][k].get('tallele1')
									y['target_a2'] = proxy_dat[j][k].get('tallele2')
									y['proxy_a1'] = proxy_dat[j][k].get('pallele1')
									y['proxy_a2'] = proxy_dat[j][k].get('pallele2')
									y['name'] = snps[j]
									matched_proxies.append(y.copy())
									flag = 1
									# print "straight", i, j, k, l
									break
								if al == "switch":
									y['proxy'] = True
									y['effect_allele'] = proxy_dat[j][k].get('tallele2')
									y['other_allele'] = proxy_dat[j][k].get('tallele1')
									y['target_a1'] = proxy_dat[j][k].get('tallele1')
									y['target_a2'] = proxy_dat[j][k].get('tallele2')
									y['proxy_a1'] = proxy_dat[j][k].get('pallele1')
									y['proxy_a2'] = proxy_dat[j][k].get('pallele2')
									y['name'] = snps[j]
									matched_proxies.append(y.copy())
									flag = 1
									# print "switch", i, j, k, l
									break
								if al == "skip":
									logger2.debug("skip")
							else:
								y['proxy'] = True
								y['target_a1'] = proxy_dat[j][k].get('tallele1')
								y['target_a2'] = proxy_dat[j][k].get('tallele2')
								y['proxy_a1'] = proxy_dat[j][k].get('pallele1')
								y['proxy_a2'] = proxy_dat[j][k].get('pallele2')
								y['name'] = snps[j]
								matched_proxies.append(dict(y))
								flag = 1
								# print "unaligned", i, j, k, l
								break
	end = time.time()
	t=round((end - start), 4)
	logger2.debug('extract_proxies_from_query took :'+str(t)+' seconds')
	return matched_proxies



def flip(x):
	if x == "A":
		return "T"
	if x == "T":
		return "A"
	if x == "G":
		return "C"
	if x == "C":
		return "G"


def allele_check(x):
	if x is None:
		return x
	x = x.upper()
	if x == "A":
		return x
	if x == "T":
		return x
	if x == "G":
		return x
	if x == "C":
		return x
	return None


def proxy_alleles(pq, pd, maf_threshold):
	mallele1 = allele_check(pq.get('effect_allele'))
	mallele2 = allele_check(pq.get('other_allele'))
	tallele1 = pd.get('tallele1')
	tallele2 = pd.get('tallele2')
	pallele1 = pd.get('pallele1')
	pallele2 = pd.get('pallele2')
	if mallele1 is None:
		return "no allele"
	pal = pd.get('pal')
	eaf = pq.get('effect_allele_freq')
	if pal == "0":
		if (mallele1 == pallele1 and mallele2 == pallele2) or (mallele1 == flip(pallele1) and mallele2 == flip(pallele2)):
			return "straight"
		if (mallele1 == pallele2 and mallele2 == pallele1) or (mallele1 == flip(pallele2) and mallele2 == flip(pallele1)):
			return "switch"
		if (mallele1 == pallele1 and mallele2 == None) or (mallele1 == flip(pallele1) and mallele2 == None):
			return "straight"
		if (mallele1 == pallele2 and mallele2 == None) or (mallele1 == flip(pallele2) and mallele2 == None):
			return "switch"
		return "skip"
	if pal == "1":
		if eaf == None:
			return "skip"
		if eaf < maf_threshold:
			if (mallele1 == pallele1 and mallele2 == pallele2) or (mallele1 == pallele1 and mallele2 == None):
				return "straight"
			if (mallele1 == flip(pallele1) and mallele2 == flip(pallele2)) or (mallele1 == flip(pallele1) and mallele2 == None):
				return "switch"
		if eaf > 1 - maf_threshold:
			if (mallele1 == pallele1 and mallele2 == pallele2) or (mallele1 == pallele1 and mallele2 == None):
				return "switch"
			if (mallele1 == flip(pallele1) and mallele2 == flip(pallele2)) or (mallele1 == flip(pallele1) and mallele2 == None):
				return "straight"
		return "skip"
