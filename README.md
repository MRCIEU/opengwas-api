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
