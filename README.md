# Local


### Clone repo

```
git clone git@github.com:MRCIEU/mr-base-api.git
```

### Obtain LD data
```
wget -O app/ld_files.tgz https://www.dropbox.com/s/yuo7htp80hizigy/ld_files.tgz?dl=0
tar xzvf app/ld_files.tgz -C app/
rm app/ld_files.tgz
```

### Create dirs

```
mkdir -p app/tmp
mkdir -p app/logs
```


### Create tunnel (need to be on VPN)
```
ssh -L 9200:localhost:9200 <username>@ieu-db-interface.epi.bris.ac.uk
```


### Create environment
```
cd app
virtualenv venv
. venv/bin/activate

pip install -r requirements.txt
```

### Tell the app you are running locally

The presence of a file called `app/local` will signify that we are running locally:

```
touch local
```

### Start the API
```
python main.py
```

### Check it
```
http://localhost:8019/
http://localhost:8019/status
http://localhost:8019/assoc/2/rs234
http://localhost:8019/gwasinfo/2
```

### Unit tests
First need to obtain an `app/mrbase.oauth` file using the TwoSampleMR R package

```r
TwoSampleMR::get_mrbase_access_token()
```

This is an interactive process that requires logging in with a browser. To run the tests, from `/app` directory

```
pytest -v
```

We can run specific groups of tests only

```
pytest -v apis/tests/test_assoc.py
```

Or specific tests only

```
pytest -v apis/tests/test_assoc.py::test_assoc_get1
```

By default it will run tests for local API located at `http://localhost:8019`. However we can run for other deployed APIs e.g.

```
pytest -v apis/tests/test_assoc.py::test_assoc_get1 --url=http://apitest.mrbase.org
```


# Production

### Clone repo

```
git clone git@github.com:MRCIEU/mr-base-api.git
cd mr-base-api
git fetch
git checkout restpluspy3
```

### Generate dirs
```
wget -O app/ld_files.tgz https://www.dropbox.com/s/yuo7htp80hizigy/ld_files.tgz?dl=0
tar xzvf app/ld_files.tgz -C app/
rm app/ld_files.tgz
mkdir -p app/tmp
mkdir -p app/logs
```

### Create image

```
docker build -t mr-base-api-restpluspy3 .
```

### Create net and attach neo4j
```
docker network create mrb-net
docker network connect  mrb-net  mrb-neo4j
```

### Create container mapping this repo to volume

```
docker create --name mr-base-restpluspy3 -p 8085:80 --volume=`pwd`/app:/app mr-base-api-restpluspy3
docker connect mrb-net mr-base-restpluspy3
docker start -i mr-base-restpluspy3
```

Check it:

```
docker logs -f mr-base-api-restpluspy3
docker rm -f mr-base-api-restpluspy3
```
