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
		git clone --recurse-submodules $source$container.git
		cd $container
	fi
	hash=$(git rev-parse HEAD)
	echo "$hash"
	docker build -t "$container":"$hash" .
	cd ../mr-base-api
}

for container in "bgc-elasticsearch" "gwas_harmonisation" "gwas_processing" "mrbase-report-module"
do
	setup $container
done
