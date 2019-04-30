#!/usr/bin/env bash
set -euo pipefail

# ensure we're up to date
git pull

# get LD data
wget -O app/ld_files.tgz https://www.dropbox.com/s/yuo7htp80hizigy/ld_files.tgz?dl=0
tar xzvf app/ld_files.tgz -C app/
rm app/ld_files.tgz

# set up dir
mkdir -p app/tmp
mkdir -p app/logs

# build latest api image
docker build -t mr-base-api-restpluspy3:latest .

# deploy api and database
docker-compose up -d