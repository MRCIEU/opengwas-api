FROM tiangolo/uwsgi-nginx-flask:python3.6

RUN echo "uwsgi_read_timeout 1200s;" > /etc/nginx/conf.d/custom_timeout.conf

# install flask app
COPY ./app /app
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
