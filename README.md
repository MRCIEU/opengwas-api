# API for IEU GWAS database

Recently moved from https://github.com/MRCIEU/mr-base-api

## Local development

Requires [Docker](https://docs.docker.com/install) install on host machine

### Clone repo
```
git clone git@ieugit-scmv-d0.epi.bris.ac.uk:gh13047/igd-api.git
cd igd-api
```

### Obtain LD data
```
mkdir -p app/ld_files
curl -o app/ld_files.tgz -L "http://fileserve.mrcieu.ac.uk/ld/data_maf0.01_rs_ref.tgz"
tar xzvf app/ld_files.tgz -C app/ld_files/
rm app/ld_files.tgz
```

### Create tunnel (need to be on VPN)
```
ssh -f -N -L 9200:140.238.83.192:9200 <username>@ieu-db-interface.epi.bris.ac.uk
```

### Create environment
```
cd app
python3.8 -m venv venv3
. venv3/bin/activate
mkdir -p data/mrb_logs
mkdir -p data/igd
mkdir -p tmp

pip install -r requirements.txt
```

### Deploy local Neo4j instance using Docker
```
docker run -d \
-p7474:7474 -p7687:7687 \
--env NEO4J_AUTH=neo4j/dT9ymYwBsrzd \
--env NEO4J_dbms_memory_heap_max__size=4G \
--name neo4j_igd \
neo4j:3.5.6
```

(Note: using neo4j:3.5.6 because it is stable and doesn't keep crashing Docker on mac)

### Importing data from MySQL
The meta data is

1. Stored as json files with the associated vcf files.
2. Collated into relational tsv files using the [igd-metadata](https://ieugit-scmv-d0.epi.bris.ac.uk/gh13047/igd-metadata) repository.
3. Uploaded to the neo4j database with `map_from_csv.py`

```
cd app
git clone git@ieugit-scmv-d0.epi.bris.ac.uk:gh13047/igd-metadata.git

# import to graph
python map_from_csv.py \
--study igd-metadata/data/study.tsv \
--groups igd-metadata/data/groups.tsv \
--permissions_e igd-metadata/data/permissions.tsv \
--memberships igd-metadata/data/memberships.tsv \
--batches igd-metadata/data/batches.tsv
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
http://localhost:8019/assoc/ieu-a-2/rs234
http://localhost:8019/gwasinfo/ieu-a-2
```

### Unit tests
First need to obtain an `app/mrbase.oauth` file using the TwoSampleMR R package

```r
TwoSampleMR::get_mrbase_access_token()
```

This is an interactive process that requires logging in with a browser. To run the tests, from `/app` directory

Set MRB token

```
export MRB_TOKEN=XXXXX
```

```
rm -f data/mrb_logs/*
rm -rf data/igd/*
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


## Production

### Clone repo
```
git clone git@ieugit-scmv-d0.epi.bris.ac.uk:gh13047/igd-api.git
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

# ld files
mkdir -p /data/ref/ld_files
curl -o ld_files.tgz -L "http://fileserve.mrcieu.ac.uk/ld/data_maf0.01_rs_ref.tgz"
tar xzvf ld_files.tgz -C /data/ref/ld_files
rm ld_files.tgz
```

### Build images for backend processing of data
```
bash build.sh
```

### Deploy
```
docker-compose -p mr-base-api-v3 -f ./docker-compose.yml up -d
```

### Test

Note the email used to obtain must be associated with all groups in the graph otherwise tests will fail, [see here](https://github.com/MRCIEU/mr-base-api/blob/3085529ee1da86184a2c7f8f6e03e2413fb0272e/app/populate_db/map_from_csv.py#L272)

```
docker-compose -p mr-base-api-v3-test -f ./docker-compose-test.yml up -d
Rscript -e "write.table(TwoSampleMR::get_mrbase_access_token(), file='token.temp', row=F, col=F, qu=F)"
bash test.sh
```

### Rebuild Neo4j database

**Caution this will erase the current Neo4j database and rebuild from MySQL CSV files. This is not part of routine deployment.**

```
# dump MySQL data to CSV
mysql -h ieu-db-interface.epi.bris.ac.uk -P 23306 -u mrbaseapp -p'M1st3rbase!' -B -N -e "select * from study_e" mrbase | sed 's/\\n//g' > study_e.tsv
mysql -h ieu-db-interface.epi.bris.ac.uk -P 23306 -u mrbaseapp -p'M1st3rbase!' -B -N -e "select * from groups" mrbase | sed 's/\\n//g' > groups.tsv
mysql -h ieu-db-interface.epi.bris.ac.uk -P 23306 -u mrbaseapp -p'M1st3rbase!' -B -N -e "select * from permissions_e" mrbase | sed 's/\\n//g' > permissions_e.tsv
mysql -h ieu-db-interface.epi.bris.ac.uk -P 23306 -u mrbaseapp -p'M1st3rbase!' -B -N -e "select * from memberships" mrbase | sed 's/\\n//g' > memberships.tsv

# copy CSV files into production container
docker cp study_e.tsv mr-base-api_mr-base-api-v3-private_1:/tmp
docker cp groups.tsv mr-base-api_mr-base-api-v3-private_1:/tmp
docker cp permissions_e.tsv mr-base-api_mr-base-api-v3-private_1:/tmp
docker cp memberships.tsv mr-base-api_mr-base-api-v3-private_1:/tmp

# import data to graph
docker exec -it mr-base-api_mr-base-api-v3-private_1 \
python map_from_csv.py \
--study /tmp/study_e.tsv \
--groups /tmp/data/groups.tsv \
--permissions_e /tmp/permissions_e.tsv \
--memberships /tmp/memberships.tsv
```

Alternatively (this is the latest method), import the data via the [igd-metadata](https://ieugit-scmv-d0.epi.bris.ac.uk/gh13047/igd-metadata) gitlab repo

```
cd app
git clone git@ieugit-scmv-d0.epi.bris.ac.uk:gh13047/igd-metadata.git

# copy CSV files into production container
docker cp igd-metadata/data/study_e.tsv mr-base-api_mr-base-api-v3-private_1:/tmp
docker cp igd-metadata/data/groups.tsv mr-base-api_mr-base-api-v3-private_1:/tmp
docker cp igd-metadata/data/permissions_e.tsv mr-base-api_mr-base-api-v3-private_1:/tmp
docker cp igd-metadata/data/memberships.tsv mr-base-api_mr-base-api-v3-private_1:/tmp

# import data to graph
docker exec -it mr-base-api_mr-base-api-v3-private_1 \
python map_from_csv.py \
--study /tmp/study_e.tsv \
--groups /tmp/data/groups.tsv \
--permissions_e /tmp/permissions_e.tsv \
--memberships /tmp/memberships.tsv
```