FROM tiangolo/uwsgi-nginx-flask:python3.6

COPY ./app /app
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
