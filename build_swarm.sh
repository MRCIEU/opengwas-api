#!/bin/bash
docker rmi flaskmrbaseapi
docker rmi 127.0.0.1:5000/flaskmrbaseapi
docker build -t flaskmrbaseapi .
docker tag flaskmrbaseapi 127.0.0.1:5000/flaskmrbaseapi
docker push 127.0.0.1:5000/flaskmrbaseapi
docker service create --replicas 3 --name mrbaseapi --publish 8019:80 127.0.0.1:5000/flaskmrbaseapi
