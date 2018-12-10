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
virtualenv venv
. venv/bin/activate

pip install -r requirements.txt
```

### Start the API
```
cd app
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

# Production

### Clone repo

```
git clone git@github.com:MRCIEU/mr-base-api.git
cd mr-base-api
git fetch
git checkout refactor
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
docker build -t mr-base-api2-image .
```

### Create container mapping this repo to volume

```
docker run -d -it --name mr-base-api2 -p 8082:8019 --volume=`pwd`/app:/app mr-base-api2-image
```

Check it:

```
docker logs -f mr-base-api2
```

