FROM tiangolo/uwsgi-nginx-flask:python3.6

# 300 seconds = 5 minutes
RUN echo "uwsgi_read_timeout 300s;" > /etc/nginx/conf.d/custom_timeout.conf

# install flask app
COPY ./app /app
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
