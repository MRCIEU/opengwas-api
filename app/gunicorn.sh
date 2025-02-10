#!/bin/bash

gunicorn --bind=0.0.0.0:80 --timeout=$GUNICORN_TIMEOUT --worker-class=gevent --workers=$(($(nproc) + 1)) main:app
