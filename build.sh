#!/bin/bash
set -euo pipefail

source='git@github.com:MRCIEU/'

# ensure we're up to date
git pull

function setup {
	cd ../
	echo $1
	container=$1
	if [ -d "$container" ]; then
		cd $container
		git pull
	else
		git clone --recurse-submodules $source$container.git
		cd $container
	fi
	hash=$(git rev-parse HEAD)
	echo "$hash"
	if [ "$container" == "mrbase-report-module" ]; then
		docker build -f ./env/Dockerfile -t "$container":"$hash" .
	else
		docker build -t "$container":"$hash" .
	fi
	cd ../mr-base-api
}

# get LD data
wget -O app/ld_files.tgz https://www.dropbox.com/s/yuo7htp80hizigy/ld_files.tgz?dl=0
tar xzvf app/ld_files.tgz -C app/
rm app/ld_files.tgz

# build latest api image
docker build -t mr-base-api-restpluspy3:latest .

# build cromwell container with Docker exec
docker build -t cromwell-docker ./app/resources/workflow

# build pipeline components
for container in "bgc-elasticsearch" "gwas_harmonisation" "gwas_processing" "mrbase-report-module"
do
	setup $container
done
