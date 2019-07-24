set -euo pipefail

mkdir -p data

mysql -h ieu-db-interface.epi.bris.ac.uk -P 13306 -u mrbaseapp -p'M1st3rbase!' -B -N -e "select * from study_e" mrbase | sed 's/\\n//g' > ./data/study_e.tsv
mysql -h ieu-db-interface.epi.bris.ac.uk -P 13306 -u mrbaseapp -p'M1st3rbase!' -B -N -e "select * from groups" mrbase | sed 's/\\n//g' > ./data/groups.tsv
mysql -h ieu-db-interface.epi.bris.ac.uk -P 13306 -u mrbaseapp -p'M1st3rbase!' -B -N -e "select * from permissions_e" mrbase | sed 's/\\n//g' > ./data/permissions_e.tsv
mysql -h ieu-db-interface.epi.bris.ac.uk -P 13306 -u mrbaseapp -p'M1st3rbase!' -B -N -e "select * from memberships" mrbase | sed 's/\\n//g' > ./data/memberships.tsv
