from flask import request
import os
import logging
import logging.handlers
from _globals import LOG_FILE, LOG_FILE_DEBUG
from _auth import *


"""

Setup logging

"""


USER_EMAIL = None

class ContextFilter(logging.Filter):
    """
    This is a filter which injects contextual information into the log.
    """
    def filter(self, record):
        record.user = get_user_email(request.headers.get('X-Api-Token'))
        return True


if not os.path.exists(LOG_FILE):
	open('file', 'w').close()

formatter=logging.Formatter('%(asctime)s %(msecs)d %(user)s %(threadName)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s',datefmt='%d-%m-%Y:%H:%M:%S')

def setup_logger(name, log_file, level=logging.INFO):
	# Create the log message rotatin file handler to the logger
	# 10000000 = 10 MB
	handler = logging.handlers.RotatingFileHandler(log_file,maxBytes=100000000, backupCount=100)
	handler.setFormatter(formatter)

	logger = logging.getLogger(name)
	logger.setLevel(level)
	logger.addHandler(handler)

	#add user email to all log messages
	user_email=ContextFilter()
	logger.addFilter(user_email)

	return logger

#create info log
logger = setup_logger('info-log', LOG_FILE)
#create debug log
logger2 = setup_logger('debug-log', LOG_FILE_DEBUG, level=logging.DEBUG)


def logger_info():
	source = request.headers.get('X-Api-Source')
	if source is None:
		source = 'url'
	i = "path: {0}; method: {1}; remote_addr1: {2}; remote_addr2: {3}; source: {4}".format(request.full_path, request.method, request.remote_addr, request.headers.get('X-Forwarded-For'), source)
	logger.info(i)

