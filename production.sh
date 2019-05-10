#!/usr/bin/env bash
set -euo pipefail

# ensure we're up to date
git pull

# stop and rm
docker stop mrb-neo4j || true
docker rm mrb-neo4j || true
docker stop mr-base-api-restpluspy3 || true
docker rm mr-base-api-restpluspy3 || true
docker network rm  mrb-net || true

# get LD data
wget -O app/ld_files.tgz https://www.dropbox.com/s/yuo7htp80hizigy/ld_files.tgz?dl=0
tar xzvf app/ld_files.tgz -C app/
rm app/ld_files.tgz

# build latest api image
docker build -t mr-base-api-restpluspy3:latest .

# create database container
docker create \
--name mrb-neo4j \
--restart always \
-p 27474:7474 \
-p 27687:7687 \
-p 27473:7473 \
-v /data/mrb_neo4j/data:/data \
-v /data/mrb_neo4j/logs:/logs \
-e NEO4J_AUTH=neo4j/dT9ymYwBsrzd \
-e NEO4J_dbms_memory_heap_max__size=10G \
-e NEO4J_dbms_memory_heap_initial__size=5G \
-e NEO4J_dbms_memory_pagecache_size=10G \
-e NEO4J_dbms_shell_enabled=true \
-e NEO4J_dbms_allow__upgrade=true \
neo4j:3.5

# create api container
docker create \
--name mr-base-api-restpluspy3 \
--restart always \
-p 8082:80 \
-v /data/bgc:/data/bgc \
-v /data/mrb_logs:/data/mrb_logs \
-e NGINX_MAX_UPLOAD=500m \
-e UWSGI_PROCESSES=20 \
-e UWSGI_THREADS=2 \
-e ENV=production \
-e ACCESS=private \
mr-base-api-restpluspy3:latest

# create network and attach
docker network create mrb-net || true
docker network connect  mrb-net  mrb-neo4j
docker network connect mrb-net mr-base-api-restpluspy3

# start
docker start mrb-neo4j
docker start mr-base-api-restpluspy3

# serve static files using h5ai
# TODO map to subdomain of API url
docker stop mrb_download || true
docker rm mrb_download || true

docker run \
-it \
-d \
--name mrb_download \
--restart always \
-p 8083:80 \
-v /data/bgc/:/var/www clue/h5ai

# start cromwell server (must be run natively)
# uses port 8000 by default and not exposed
cd /data/cromwell
nohup java \
-Ddocker.hash-lookup.enabled=false \
-Dsystem.max-concurrent-workflows=1 \
-Dbackend.providers.Local.config.root="/data/cromwell-executions" \
-Dworkflow-options.workflow-log-dir="/data/cromwell-workflow-logs" \
-jar cromwell-40.jar \
server &
