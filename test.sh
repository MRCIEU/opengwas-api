#!/usr/bin/env bash
set -euo pipefail

# get TwoSampleMR token
token=$(cat ./token.temp)

# get test data for graph
mysql -h ieu-db-interface.epi.bris.ac.uk -P 13306 -u mrbaseapp -p'M1st3rbase!' -B -N -e "select * from study_e" mrbase | sed 's/\\n//g' > /tmp/study_e.tsv
mysql -h ieu-db-interface.epi.bris.ac.uk -P 13306 -u mrbaseapp -p'M1st3rbase!' -B -N -e "select * from groups" mrbase | sed 's/\\n//g' > /tmp/groups.tsv
mysql -h ieu-db-interface.epi.bris.ac.uk -P 13306 -u mrbaseapp -p'M1st3rbase!' -B -N -e "select * from permissions_e" mrbase | sed 's/\\n//g' > /tmp/permissions_e.tsv
mysql -h ieu-db-interface.epi.bris.ac.uk -P 13306 -u mrbaseapp -p'M1st3rbase!' -B -N -e "select * from memberships" mrbase | sed 's/\\n//g' > /tmp/memberships.tsv

# import data to graph
docker exec -it mr-base-api-v2-test python populate_db/map_from_csv.py \
--study /tmp/study_e.tsv \
--groups /tmp/groups.tsv \
--permissions_e /tmp/permissions_e.tsv \
--memberships /tmp/memberships.tsv

# run unit API tests
docker exec -e MRB_TOKEN="$token" -it mr-base-api-v2-test pytest -v apis/ --url http://localhost
docker exec -e MRB_TOKEN="$token" -it mr-base-api-v2-test pytest -v resources/
docker exec -e MRB_TOKEN="$token" -it mr-base-api-v2-test pytest -v schemas/
docker exec -e MRB_TOKEN="$token" -it mr-base-api-v2-test pytest -v queries/

# take down
docker-compose -p mr-base-api-v2-test -f ./docker-compose-test.yml down
