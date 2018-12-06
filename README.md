# Local


### Clone repo

```
git clone git@github.com:MRCIEU/mr-base-api.git
```

### Copy of ld data
```
wget -O app/ld_files.tgz https://www.dropbox.com/s/yuo7htp80hizigy/ld_files.tgz?dl=0
tar xzvf app/ld_files.tgz -C app/
rm app/ld_files.tgz
```

### Edit conf for elasticsearch (app/conf_files/es_conf.json)
```
{
        "host": "localhost",
        "port":9200
}
```

### Create tunnel (need to be on VPN)
```
ssh -NL 9200:localhost:9200 ieu-db-interface.epi.bris.ac.uk
```

### Edit the API port
```
if __name__ == "__main__":
        #app.run(host='0.0.0.0', debug=True, port=80)
        app.run(host='0.0.0.0', debug=True, port=8019)
```

### Create environment
```
virtualenv venv
. venv/bin/activate

pip install -r requirements.txt
```

### Start the API
```
python main.py
```

### Check it
```
http://localhost:8019/get_effects?access_token=api_test&outcomes=UKB-a:1&snps=rs123
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
