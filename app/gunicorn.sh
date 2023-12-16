#!/bin/bash

gunicorn --bind=0.0.0.0:80 --timeout=300 --worker-class=gevent --workers=$(($(nproc) + 1)) main:app
