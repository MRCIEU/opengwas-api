FROM tiangolo/uwsgi-nginx-flask:python3.6

COPY ./app /app
COPY ./app/custom.conf /etc/nginx/conf.d/
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
