FROM tiangolo/uwsgi-nginx-flask:python3.6.4

COPY ./app/requirements.txt /app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
