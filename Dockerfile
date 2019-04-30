FROM tiangolo/uwsgi-nginx-flask:python3.6

# install flask app
COPY ./app /app
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
