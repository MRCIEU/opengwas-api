#!/bin/bash

gunicorn --bind=0.0.0.0:80 --timeout=300 --workers=$(($(nproc) + 1)) main:app
