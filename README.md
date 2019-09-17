# Local


### Clone repo

```
git clone git@github.com:MRCIEU/mr-base-api.git
cd mr-base-api
git fetch
```

### Obtain LD data
```
wget -O app/ld_files.tgz https://www.dropbox.com/s/yuo7htp80hizigy/ld_files.tgz?dl=0
tar xzvf app/ld_files.tgz -C app/
rm app/ld_files.tgz
```

### Create tunnel (need to be on VPN)
```
ssh -L 9200:localhost:9200 <username>@ieu-db-interface.epi.bris.ac.uk
```

### Create environment
```
cd app
python3 -m venv venv3
. venv3/bin/activate
mkdir -p data/mrb_logs
mkdir -p data/igd

pip install -r requirements.txt
```

### Importing mysql data

Create a Neo4j container e.g. using:

```
version: '3'
services:
#neo4j
   db:
    image: neo4j:3.5
    restart: always
    container_name: mrb-neo4j-dev
    #comment out ports to lock down neo4j
    ports:
     - "37474:7474"
     - "37687:7687"
     - "37473:7473"
    environment:
     - NEO4J_AUTH=neo4j/xxxxx # configure the instance with custom username/password
     - NEO4J_dbms_memory_heap_max__size=10G # configure the heap memory
     - NEO4J_dbms_memory_heap_initial__size=5G
     - NEO4J_dbms_memory_pagecache_size=10G # configure the cache memory
     - NEO4J_dbms_shell_enabled=true
     - NEO4J_dbms_directories_import=import
     - NEO4J_dbms_allow__upgrade=true
     - NEO4J_dbms_security_allow__csv__import__from__file__urls=true
    volumes:
     - /data/mrb_neo4j_dev2/data:/data
     - /data/mrb_neo4j_dev2/import:/var/lib/neo4j/import
```

Make sure that `conf_data/app_config.json` is configured correctly for this container. Now populate:

```
cd app/populate_db

# Download data from mysql
bash get_csv.sh

# import to graph
python map_from_csv.py
```

### Start the API
```
export FLASK_ENV=development
python main.py
```

### Check it
```
http://localhost:8019/
http://localhost:8019/status
http://localhost:8019/assoc/2/rs234
http://localhost:8019/gwasinfo/2
```

### Unit tests
First need to obtain an `app/mrbase.oauth` file using the TwoSampleMR R package

```r
TwoSampleMR::get_mrbase_access_token()
```

This is an interactive process that requires logging in with a browser. To run the tests, from `/app` directory

```
pytest -v
```

We can run specific groups of tests only

```
pytest -v apis/tests/test_assoc.py
```

Or specific tests only

```
pytest -v apis/tests/test_assoc.py::test_assoc_get1
```

By default it will run tests for local API located at `http://localhost:8019` (defined here `apis/tests/conftest.py`. However we can run for other deployed APIs e.g.

```
pytest -v apis/tests/test_assoc.py::test_assoc_get1 --url http://apitest.mrbase.org
```


# Production

### Clone repo

```
git clone git@github.com:MRCIEU/mr-base-api.git
cd mr-base-api
git fetch
```

### Copy reference data from RDSF

```
# reference FASTA
mkdir -p /data/reference_genomes
mkdir -p /data/reference_genomes/released
rsync -av bluecrystalp3.acrc.bris.ac.uk:/projects/MRC-IEU/research/data/broad/public/reference_genomes/released/2019-08-30 /data/reference_genomes/released

# dbsnp
mkdir -p /data/dbsnp
mkdir -p /data/dbsnp/released
rsync -av bluecrystalp3.acrc.bris.ac.uk:/projects/MRC-IEU/research/data/ncbi/public/dbsnp/released/2019-09-11 /data/dbsnp/released
```

### Build images for backend processing of data
```
bash build.sh
```

### Deploy
```
docker-compose -p mr-base-api-v2 -f ./docker-compose.yml up -d
```

### Test

Note the email used to obtain must be associated with all groups in the graph otherwise tests will fail, [see here](https://github.com/MRCIEU/mr-base-api/blob/3085529ee1da86184a2c7f8f6e03e2413fb0272e/app/populate_db/map_from_csv.py#L272)

```
docker-compose -p mr-base-api-v2-test -f ./docker-compose-test.yml up -d
Rscript -e "write.table(TwoSampleMR::get_mrbase_access_token(), file='token.temp', row=F, col=F, qu=F)"
bash test.sh
```
