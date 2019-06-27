#!/bin/bash
set -euo pipefail

source='git@github.com:MRCIEU/'

git pull

function setup {
	cd ../
	echo $1
	container=$1
	if [ -d "$container" ]; then
		cd $container
		git pull
	else
		git clone $source$container.git
		cd $container
	fi
	hash=$(git rev-parse HEAD)
	echo "$hash"
	docker build -t "$container":"$hash" .
	cd ../mr-base-api
}

for container in "bgc-elasticsearch" "gwas_harmonisation" "gwas_processing"
do
	setup $container
done

# non master branch
cd ../"mrbase-report-module"
git checkout wdl
cd ../mr-base-api
setup "mrbase-report-module"
