FROM tiangolo/uwsgi-nginx-flask:python3.6

#RUN echo "uwsgi_read_timeout 600s;" > /etc/nginx/conf.d/custom_timeout.conf
#RUN echo "client_max_body_size 750M;" > /etc/nginx/conf.d/custom_upload.conf

# install flask app
COPY ./app /app
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
