FROM tiangolo/uwsgi-nginx-flask:python3.6

RUN echo "uwsgi_read_timeout 1200s;" > /etc/nginx/conf.d/custom_timeout.conf

# install flask app
COPY ./app /app
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# make dirs
RUN mkdir /data
RUN mkdir /data/igd
RUN mkdir /data/mrb_logs
RUN mkdir /data/tmp
RUN mkdir /ld_files

# copy in parameters
COPY ../conf_files/app_conf.json /app