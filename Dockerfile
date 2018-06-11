FROM tiangolo/uwsgi-nginx-flask:flask

#COPY ./app /app
COPY ./app/requirements.txt /app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
#RUN apt-get install vim
