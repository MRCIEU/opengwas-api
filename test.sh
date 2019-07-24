#!/usr/bin/env bash
set -euo pipefail

# get TwoSampleMR token
token=$(cat ./token.temp)

# get test data for graph
mysql -h ieu-db-interface.epi.bris.ac.uk -P 13306 -u mrbaseapp -p'M1st3rbase!' -B -N -e "select * from study_e" mrbase > /tmp/study_e.tsv
mysql -h ieu-db-interface.epi.bris.ac.uk -P 13306 -u mrbaseapp -p'M1st3rbase!' -B -N -e "select * from groups" mrbase > /tmp/groups.tsv
mysql -h ieu-db-interface.epi.bris.ac.uk -P 13306 -u mrbaseapp -p'M1st3rbase!' -B -N -e "select * from permissions_e" mrbase > /tmp/permissions_e.tsv
mysql -h ieu-db-interface.epi.bris.ac.uk -P 13306 -u mrbaseapp -p'M1st3rbase!' -B -N -e "select * from memberships" mrbase > /tmp/memberships.tsv

# import data to graph
docker exec -it mr-base-api-restpluspy3-test python populate_db/map_from_csv.py

# run unit API tests
docker exec -e MRB_TOKEN="$token" -it mr-base-api-restpluspy3-test pytest -v apis/ --url http://localhost
docker exec -e MRB_TOKEN="$token" -it mr-base-api-restpluspy3-test pytest -v resources/
docker exec -e MRB_TOKEN="$token" -it mr-base-api-restpluspy3-test pytest -v schemas/
docker exec -e MRB_TOKEN="$token" -it mr-base-api-restpluspy3-test pytest -v queries/

# take down
docker-compose -p mr-base-api-restpluspy3-test -f ./docker-compose-test.yml down
