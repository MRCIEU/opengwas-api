
# Notes on query logs

server=xxx

### elastic_query_phewas_rsid

`curl -XGET "$server:8019/phewas/rs1205/0.001"`

### elastic_query_phewas_chrpos

`curl -XGET "http://$server:8019/phewas//7%3A105561135/0.001"`

### elastic_query_phewas_cprange

`curl -XGET "http://$server:8019/phewas/7%3A105561135-105563135/0.001"`

### elastic_query_chrpos

`curl -XGET "http://$server:8019/associations/ieu-a-1/3%3A186461181"`

### elastic_query_cprange

`curl -XGET "http://$server:8019/associations/ieu-a-1/7%3A105561135-105563135"`

### elastic_query_rsid

`curl -XGET "http://$server:8019/associations/ieu-a-1/rs1205"`

### elastic_query_pval

`curl -X POST "http://$server:8019/tophits?id=ieu-a-1&pval=0.0001&preclumped=1&clump=1&bychr=1&r2=0.001&kb=5000&pop=EUR" -H "accept: application/json" -H "X-Api-Token: null"`