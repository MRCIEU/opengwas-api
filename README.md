Create docker network bridge

```
docker network create -d bridge mrbase_bridge
```

Start up Elasticsearch container

```
docker run -d --net mrbase_bridge -e "discovery.type=single-node" -e ES_JAVA_OPTS="-Xms30g -Xmx30g" --volume=$HOME/mrbase/data:/data --volume=$HOME/elastic-data:/usr/share/elasticsearch/data --name mr-base-elastic-docker-bridge docker.elastic.co/elasticsearch/elasticsearch:5.6.2
```

Create API container

```
docker build .
```

Start up API container using network

```
docker run -d --net mrbase_bridge -e DB=mr-base-elastic-docker-bridge --name mrbase-api-es-bridge -p 8080:80 f2ddb5c4dde8
```
