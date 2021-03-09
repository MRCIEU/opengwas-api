
# Notes on query logs

server=localhost:8019
server=gwas-api.mrcieu.ac.uk

### phewas_rsid

PheWAS query using rsid
- searches the entire set of records using list of rsids and pvalue 

API function name:
- elastic_query_phewas_rsid

API:
- `curl -XGET "http://$server/phewas/rs1205/0.001"`

Log:
- `name:phewas_rsid	time:0.5915	    hits:84	     rsid:['rs4343']	pval:0.001	indexes:['prot-c',.....]`


### phewas_chrpos

PheWAS query using chromosome and position
- searches the entire set of records using chromosome name and position

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


### elastic_query_chrpos

`curl -XGET "http://$server/associations/ieu-a-1/3%3A186461181"`

### elastic_query_cprange

`curl -XGET "http://$server/associations/ieu-a-1/7%3A105561135-105563135"`

### elastic_query_rsid

`curl -XGET "http://$server/associations/ieu-a-1/rs1205"`

### elastic_query_pval

`curl -X POST "http://$server/tophits?id=ieu-a-1&pval=0.0001&preclumped=1&clump=1&bychr=1&r2=0.001&kb=5000&pop=EUR" -H "accept: application/json" -H "X-Api-Token: null"`
