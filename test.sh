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
-e MRB_TOKEN="ya29.Glv9BqTugIA9tvEloR5-posYl55SAwApwhPn0vJgzSLIBo8vOvcoeDM-zKu3vBaVaAt3y_PPJ4qQagFWi6_syQfmiHjPfG3Z1mzPO5RCZ7CxEHiOCpnOBIPovs4g" \
mr-base-api-restpluspy3:latest

# attach
docker network connect mrb-net mr-base-api-restpluspy3-tests

# run tests
docker start mr-base-api-restpluspy3-tests
docker exec -it mr-base-api-restpluspy3-tests pytest -v
