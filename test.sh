#!/usr/bin/env bash
set -euo pipefail

#### WARNING running tests will ERASE ALL DATA in the neo4j ###
### set up a test database before proceeding ###

# ensure we're up to date
git pull

# stop and rm
docker stop mr-base-api-restpluspy3-tests || true
docker rm mr-base-api-restpluspy3-tests || true

# make tmp output for data
tmpdir=$(mktemp -d)

# run unit tests
# obtain token.temp from TwoSampleMR
docker create \
--name mr-base-api-restpluspy3-tests \
-v /data/bgc:/data/bgc \
-v "$tmpdir":/data/mrb_logs \
-e NGINX_MAX_UPLOAD=500m \
-e NGINX_UWSGI_READ_TIMEOUT=300 \
-e UWSGI_PROCESSES=20 \
-e UWSGI_THREADS=2 \
-e ENV=production \
-e ACCESS=private \
-e MRB_TOKEN=$(cat token.temp | tr -d '\n') \
mr-base-api-restpluspy3:latest

# attach to network
docker network connect mrb-net mr-base-api-restpluspy3-tests

# start container
docker start mr-base-api-restpluspy3-tests
sleep 15

# run tests
docker exec -it mr-base-api-restpluspy3-tests pytest -v apis/ --url http://localhost
docker exec -it mr-base-api-restpluspy3-tests pytest -v resources/
docker exec -it mr-base-api-restpluspy3-tests pytest -v schemas/
docker exec -it mr-base-api-restpluspy3-tests pytest -v queries/
