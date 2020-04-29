# API for IEU GWAS database

Recently moved from <https://github.com/MRCIEU/mr-base-api>

## Clone repo

```sh
git clone git@ieugit-scmv-d0.epi.bris.ac.uk:gh13047/igd-api.git
```

## Local development

Requires [Docker](https://docs.docker.com/install) install on host machine

### Obtain LD data

```sh
cd igd-api
mkdir -p app/ld_files
curl -o app/ld_files.tgz -L "http://fileserve.mrcieu.ac.uk/ld/data_maf0.01_rs_ref.tgz"
tar xzvf app/ld_files.tgz -C app/ld_files/
rm app/ld_files.tgz
```

### Create tunnel (need to be on VPN)

```sh
ssh -f -N -L 9200:140.238.83.192:9200 <username>@ieu-db-interface.epi.bris.ac.uk
```

### Create environment

```sh
cd app
python3.8 -m venv venv3
. venv3/bin/activate
mkdir -p data/mrb_logs
mkdir -p data/igd
mkdir -p tmp

pip install -r requirements.txt
```

### Deploy local Neo4j instance using Docker

```sh
docker run -d \
-p7474:7474 -p7687:7687 \
--env NEO4J_AUTH=neo4j/dT9ymYwBsrzd \
--env NEO4J_dbms_memory_heap_max__size=4G \
--name neo4j_igd \
neo4j:3.5.6
```

(Note: using neo4j:3.5.6 because it is stable and doesn't keep crashing Docker on mac)

### Importing metadata from TSV

The meta data is

1. Stored as json files with the associated vcf files.
2. Collated into relational tsv files using the [igd-metadata](https://ieugit-scmv-d0.epi.bris.ac.uk/gh13047/igd-metadata) repository.
3. Uploaded to the neo4j database with `map_from_csv.py`

```sh
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

```sh
export FLASK_ENV=development
python main.py
```

### Check it

- <http://localhost:8019/>
- <http://localhost:8019/status>
- <http://localhost:8019/associations/ieu-a-2/rs234>
- <http://localhost:8019/gwasinfo/ieu-a-2>

### Local unit tests

For testing prior to deployment [run the tests in a container](#Production-unit-tests). These instructions are for adhoc testing.

Use the same Python3 env as the API

```sh
cd app
. venv3/bin/activate
```

Create an access token [using these instructions](#Generate-access-token).

Note the email used to obtain the token must be associated with all groups in the graph otherwise tests will fail, [see here](app/map_from_csv.py#L306)

```sh
rm -f data/mrb_logs/*
rm -rf data/igd/*
pytest -v
```

We can run specific groups of tests only

```sh
pytest -v apis/tests/test_assoc.py
```

Or specific tests only

```sh
pytest -v apis/tests/test_assoc.py::test_assoc_get1
```

By default it will run tests for local API located at `http://localhost:8019` (defined here `apis/tests/conftest.py`. However we can run for other deployed APIs e.g.

```sh
pytest -v apis/tests/test_assoc.py::test_assoc_get1 --url https://gwas-api.mrcieu.ac.uk
```

## Production

### Checkout specific release

```
git fetch && git fetch --tags
git checkout 3.3.4
```

### Build images for backend processing of data

```sh
cd igd-api
bash build.sh
```

### Copy reference data from RDSF

```sh
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

### Production unit tests

Create an access token [using these instructions](#Generate-access-token) and copy the ```token.temp``` file into the ```app``` folder

Note the email used to obtain the token must be associated with all groups in the graph otherwise tests will fail, [see here](app/map_from_csv.py#L306)

```sh
# build test stack
docker-compose -p mr-base-api-v3-test -f ./docker-compose-test.yml up -d
# import metadata in test Neo4J instance and run tests
bash test.sh
```

### Deploy

```sh
docker-compose -p mr-base-api-v3 -f ./docker-compose.yml up -d
```

### Rebuild Neo4j database

**Caution this will erase the current Neo4j database and rebuild from TSV files. This is NOT part of routine deployment.**

Import the data via the [igd-metadata](https://ieugit-scmv-d0.epi.bris.ac.uk/gh13047/igd-metadata) gitlab repo

```sh
cd app
git clone git@ieugit-scmv-d0.epi.bris.ac.uk:gh13047/igd-metadata.git

# copy CSV files into production container
docker cp igd-metadata/data/study.tsv mr-base-api-v3_mr-base-api-v3-private_1:/tmp
docker cp igd-metadata/data/groups.tsv mr-base-api-v3_mr-base-api-v3-private_1:/tmp
docker cp igd-metadata/data/permissions.tsv mr-base-api-v3_mr-base-api-v3-private_1:/tmp
docker cp igd-metadata/data/memberships.tsv mr-base-api-v3_mr-base-api-v3-private_1:/tmp
docker cp igd-metadata/data/batches.tsv mr-base-api-v3_mr-base-api-v3-private_1:/tmp

# import data to graph
docker exec -it mr-base-api-v3_mr-base-api-v3-private_1 \
python map_from_csv.py \
--study /tmp/study.tsv \
--groups /tmp/groups.tsv \
--permissions_e /tmp/permissions.tsv \
--memberships /tmp/memberships.tsv \
--batches /tmp/batches.tsv

# Restart container to updates batches from the new database
docker restart mr-base-api-v3_mr-base-api-v3-private_1
docker restart mr-base-api-v3_mr-base-api-v3-public_1

# Update the cache
curl http://ieu-db-interface.epi.bris.ac.uk:8082/gicache
```

## Generate access token

First need to obtain an `app/ieugwasr_oauth` file using the [ieugwasr](https://github.com/MRCIEU/ieugwasr) R-package

```sh
cd app
Rscript -e "write.table(ieugwasr::get_access_token(), file='token.temp', row=F, col=F, qu=F)"
```

This is an interactive process that requires logging in with a browser.

The token is valid for 10 minutes and will require recreating after that period.
