FROM tiangolo/uwsgi-nginx-flask:python3.6

# configure nginx
ENV NGINX_MAX_UPLOAD 500m
ENV NGINX_UWSGI_READ_TIMEOUT 300

# configure API
ENV ENV="production"
ENV ACCESS="public"

# install flask app
COPY ./app /app
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
