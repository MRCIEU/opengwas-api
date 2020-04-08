#!/usr/bin/env bash
set -euo pipefail

# get TwoSampleMR token
token=$(cat ./token.temp)

# get test data for graph
cd app
if [ ! -d "igd-metadata" ]; then
    git clone git@ieugit-scmv-d0.epi.bris.ac.uk:gh13047/igd-metadata.git
fi
cp igd-metadata/data/*.tsv /tmp

# import data to graph
docker exec -it mr-base-api-v3-test python map_from_csv.py \
--study /app/populate_db/data/study.tsv \
--groups /app/populate_db/data/groups.tsv \
--permissions_e /app/populate_db/data/permissions.tsv \
--memberships /app/populate_db/data/memberships.tsv \
--batches /app/populate_db/data/batches.tsv

# run unit API tests
docker exec -e MRB_TOKEN="$token" -it mr-base-api-v3-test pytest -v apis/ --url http://localhost
docker exec -e MRB_TOKEN="$token" -it mr-base-api-v3-test pytest -v resources/
docker exec -e MRB_TOKEN="$token" -it mr-base-api-v3-test pytest -v schemas/
docker exec -e MRB_TOKEN="$token" -it mr-base-api-v3-test pytest -v queries/

# take down
docker-compose -p mr-base-api-v3-test -f ./docker-compose-test.yml down
