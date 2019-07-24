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
ssh -L 9200:localhost:9200 <username>@ieu-db-interface.epi.bris.ac.uk
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
cd app/populate_db

# export from MySQL
mysql -h ieu-db-interface.epi.bris.ac.uk -P 13306 -u mrbaseapp -p -B -N -e "select * from study_e" mrbase | sed 's/\\n//g' > ./data/study_e.tsv
mysql -h ieu-db-interface.epi.bris.ac.uk -P 13306 -u mrbaseapp -p -B -N -e "select * from groups" mrbase | sed 's/\\n//g' > ./groups.tsv
mysql -h ieu-db-interface.epi.bris.ac.uk -P 13306 -u mrbaseapp -p -B -N -e "select * from permissions_e" mrbase | sed 's/\\n//g' > ./data/permissions_e.tsv
mysql -h ieu-db-interface.epi.bris.ac.uk -P 13306 -u mrbaseapp -p -B -N -e "select * from memberships" mrbase | sed 's/\\n//g' > ./data/memberships.tsv

# import to graph
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

### Build images for backend processing of data
```
bash build.sh
```

### Deploy
```
docker-compose -p mr-base-api-restpluspy3 -f ./docker-compose.yml up -d
```

### Test

Note the email used to obtain must be assocaited with all groups in the graph otherwise tests will fail, [see here](https://github.com/MRCIEU/mr-base-api/blob/3085529ee1da86184a2c7f8f6e03e2413fb0272e/app/populate_db/map_from_csv.py#L272)

```
docker-compose -p mr-base-api-restpluspy3-test -f ./docker-compose-test.yml up -d
Rscript -e "write.table(TwoSampleMR::get_mrbase_access_token(), file='token.temp', row=F, col=F, qu=F)"
bash test.sh
```
