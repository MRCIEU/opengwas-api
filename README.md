# Local


### Clone repo

```
git clone git@github.com:MRCIEU/mr-base-api.git
cd mr-base-api
git fetch
git checkout restpluspy3
```

### Obtain LD data
```
wget -O app/ld_files.tgz https://www.dropbox.com/s/yuo7htp80hizigy/ld_files.tgz?dl=0
tar xzvf app/ld_files.tgz -C app/
rm app/ld_files.tgz
```

### Create tunnel (need to be on VPN)
```
ssh -L 8000:localhost:8000 9200:localhost:9200 <username>@ieu-db-interface.epi.bris.ac.uk
```


### Create environment
```
cd app
virtualenv venv
. venv/bin/activate

pip install -r requirements.txt
```

### importing mysql data

```
# copy data to import folder
cp groups.tsv app/populate_db/data
cp memberships.tsv app/import/data
cp permissions_e.tsv app/import/data
cp study_e.tsv app/import/data

cd app/populate_db
python map_from_csv.py
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
### WARNING tests will erase the database. Ensure you are using a development instance of Neo4j ###
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

By default it will run tests for local API located at `http://localhost:8019` (defined here `apis/tests/conftest.py`. However we can run for other deployed APIs e.g.

```
pytest -v apis/tests/test_assoc.py::test_assoc_get1 --url http://apitest.mrbase.org
```


# Production

### Clone repo

```
git clone git@github.com:MRCIEU/mr-base-api.git
cd mr-base-api
git fetch
git checkout restpluspy3
```

### deploy
```bash production.sh```

### test
### WARNING this will erase the Neo4j database ####
```bash test.sh```
