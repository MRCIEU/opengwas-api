#!/usr/bin/env bash
set -euo pipefail

docker exec -it opengwas-api-og-api-1 python -m pytest -v -s apis/ --url http://localhost
