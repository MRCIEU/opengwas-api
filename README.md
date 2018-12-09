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

### Edit app/resources/_globals.py

Toggle between the two versions of the config file

```
ES_CONF = "./conf_files/es_conf_local.json"
# ES_CONF = "./conf_files/es_conf_deploy.json"

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


# Production

### Clone repo

```
git clone git@github.com:MRCIEU/mr-base-api.git
```

### Copy of ld data
```
cp -r /path/to/ld_files app/
```

### Create image

```
docker build -t mrbase-api-image .
```

### Create container mapping this repo to volume

```
docker run -d -it --name mrbase-api -p 8080:80 --volume=/var/www/api/mr-base-api/app:/app mrbase-api-image
```
