import os
import logging
import logging.handlers
from _globals import LOG_FILE, LOG_FILE_DEBUG


"""

Setup logging

"""

class ContextFilter(logging.Filter):
    """
    This is a filter which injects contextual information into the log.
    """
    def filter(self, record):
        # token = request.args.get('access_token')
        # record.user = get_user_email(token)
        token = "no_token_yet"
        record.user = "fake_user"
        #print record.user
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

