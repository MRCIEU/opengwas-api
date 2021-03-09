
# Notes on query logs

server=`gwas-api.mrcieu.ac.uk`

### phewas_rsid

PheWAS query using rsid
- searches the entire set of records using list of SNP IDs and P-value filter 

API function name:
- elastic_query_phewas_rsid

API:
- `curl -XGET "http://$server/phewas/rs1205/0.001"`

Log:
- `name:phewas_rsid	time:0.5915	    hits:84	     rsid:['rs4343']	pval:0.001	indexes:['prot-c',.....]`


### phewas_chrpos

PheWAS query using chromosome and position
- searches the entire set of records using chromosome name and base position

API function name:
- elastic_query_phewas_chrpos

API:
- `curl -XGET "http://$server/phewas/7%3A105561135/0.001"`

Log:
- `name:phewas_chrpos	time1.2809	hits:11	chrpos:[{'chr': 7, 'start': 105561135, 'end': 105561135, 'type': 'position', 'orig': '7:105561135'}]	pval:0.001	indexes:['prot-c',...]`

### phewas_cprange

PheWAS query using chromosome and poistion range
- searches the entire set of records uing chromosome name and range

API function name:
- elastic_query_phewas_cprange

API:
- `curl -XGET "http://$server/phewas/7%3A105561135-105563135/0.001"`

Log:
- `name:phewas_cprange	time:2.1037	hits:208	cprange:[{'chr': 7, 'start': 105561135, 'end': 105563135, 'type': 'range', 'orig': '7:105561135-105563135'}]	pval:0.001	indexes:['prot-c',...]`


### chrpos

Standard query using list of GWAS IDs, chromosome and position
- searches specific GWAS using chromosome name and base position

API function name:
- elastic_query_chrpos

API:
- `curl -XGET "http://$server/associations/ieu-a-1/3%3A186461181"`

Log:
- `name:chrpos	        time:0.0336	    hits:1	     chrpos:[{'chr': 6, 'start': 31486158, 'end': 31486158, 'type': 'position', 'orig': '6:31486158'}]	gwas:['bbj-a-148']	indexes:{'bbj-a': ['148']}`

### cprange 

Standard query using list of GWAS IDs, chromosome position and range
- searches specific GWAS using chromosome position and range

API function name:
- elastic_query_cprange

API:
- `curl -XGET "http://$server/associations/ieu-a-1/7%3A105561135-105563135"`

Log:
- `name:cprange	    time:0.4407	    hits:3099	 cprange:[{'chr': 10, 'start': 11750620, 'end': 12750620, 'type': 'range', 'orig': '10:11750620-12750620'}]	gwas['ukb-b-12948']	indexes{'ukb-b': ['12948']}`

### rsid

Standard query using list of GWAS IDs and list of SNP IDs
- searches specific GWAS and SNPs

API function name:
- elastic_query_rsid

API:
- `curl -XGET "http://$server/associations/ieu-a-1/rs1205"`

Log:
- `name:rsid           time:0.0328     hits:1       rsid:['rs75438046', 'rs1808192']    gwas:['finn-a-C3_CORPUS_UTERI']  indexes:{'finn-a': ['C3_CORPUS_UTERI']}`

### pval

Tophits query searching separate set of tophits data
- the tophits data set is a very small curated subset of all data

API function name:
- elastic_query_pval

API:
- `curl -X POST "http://$server/tophits?id=ieu-a-1&pval=0.0001&preclumped=1&clump=1&bychr=1&r2=0.001&kb=5000&pop=EUR" -H "accept: application/json" -H "X-Api-Token: null"`

Log:
- `name:pval	        time:0.4632	    hits:68	     pval:5e-08	   gwas:['ieu-a-1095']	 indexes:{'ieu-a': ['1095']}`

# Example call frequencies 

~250k queries 

- rsid: 181396 
- cprange: 41331
- pval: 11268 
- phewas_rsid: 736
- chrpos: 93
- phewas_chrpos: 7 
- phewas_cprange: 6 


