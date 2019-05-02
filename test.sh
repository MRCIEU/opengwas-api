#!/usr/bin/env bash
set -euo pipefail

#### WARNING running tests will ERASE ALL DATA in the neo4j ###
### set up a test database before proceeding ###

# ensure we're up to date
git pull

# stop and rm
docker stop mr-base-api-restpluspy3-tests || true
docker mr-base-api-restpluspy3-tests || true

# make tmp output for data
tmpdir=$(mktemp -d)

# run unit tests
# obtain token from TwoSampleMR
docker create \
--name mr-base-api-restpluspy3-tests \
-v "$tmpdir":/data/bgc \
-v "$tmpdir":/data/mrb_logs \
-e NGINX_MAX_UPLOAD=500m \
-e NGINX_UWSGI_READ_TIMEOUT=300 \
-e UWSGI_PROCESSES=20 \
-e UWSGI_THREADS=2 \
-e ENV=production \
-e ACCESS=private \
-e MRB_TOKEN= \
mr-base-api-restpluspy3:latest

# create network and attach
docker network connect  mrb-net  mrb-neo4j
docker network connect mrb-net mr-base-api-restpluspy3-tests

# run tests
docker start mr-base-api-restpluspy3-tests
docker exec -it pytest mr-base-api-restpluspy3-tests