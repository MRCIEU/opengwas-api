# Orchestrating GWAS uploads

## Description

Implementing the strategy outlined here [https://github.com/MRCIEU/mr-base-structure/blob/master/upload-system.md#pipeline](https://github.com/MRCIEU/mr-base-structure/blob/master/upload-system.md#pipeline). There are several modules that each run in a separate container.

Each of those containers can be run like this:

```
docker run \
--rm \
-v ${MountDir}:${MountDir} \
<module_name>:<hash> <module_command>
```

But we need to orchestrate when each of the modules are run. This is achieved using [Cromwell](https://cromwell.readthedocs.io/en/stable/) which is a workflow management system designed for scientific workflows. Cromwell is an interpreter for workflow instructions using [WDL](https://software.broadinstitute.org/wdl/) which is executed using the command line or on a remote host by running in web server mode.

## Running Cromwell in server mode

See available configuration here: https://cromwell.readthedocs.io/en/develop/Configuring/

```
# build cromwell including Docker executable
docker build -t cromwell-docker .

# start server
docker run \
--name <name> \
-it \
-d \
-e JAVA_OPTS="-Ddocker.hash-lookup.enabled=false -Dsystem.max-concurrent-workflows=1 -Dbackend.providers.Local.config.root=/path/to/cromwell-executions -Dworkflow-options.workflow-log-dir=/path/to/cromwell-workflow-logs" \
-p 8000:8000 \
-v /var/run/docker.sock:/var/run/docker.sock \
-v /path/to/cromwell-executions:/path/to/cromwell-executions \
-v /path/to/cromwell-workflow-logs:/path/to/cromwell-workflow-logs \
cromwell-docker \
server
```

This will start a web server allowing workflow execution over REST. Visit ```http:<hostname>:<port>``` to view Swagger documentation.

## Execute a workflow

The return json will include a unique identifier for the job

```
curl -X POST --header "Accept: application/json" \
-v "http:<hostname>:<port>/api/workflows/v1" \
-F workflowSource=@workflow.wdl \
-F workflowInputs=@params.json  
```

## Check status

```
curl http:<hostname>:<port>/api/workflows/v1/<CROMWELL_ID>/status
```

## Access runtime logs

```
cd /data/cromwell-workflow-logs/<CROMWELL_ID>
```