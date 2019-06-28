FROM tiangolo/uwsgi-nginx-flask:python3.6
ENV NGINX_MAX_UPLOAD 750m

RUN echo "uwsgi_read_timeout 600s;" > /etc/nginx/conf.d/custom_timeout.conf

# install flask app
COPY ./app /app
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
