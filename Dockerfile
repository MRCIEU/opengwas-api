FROM tiangolo/uwsgi-nginx-flask:flask

COPY ./app /app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
