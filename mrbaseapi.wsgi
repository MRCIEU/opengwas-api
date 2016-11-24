import os,sys
from werkzeug.wsgi import DispatcherMiddleware
activate_this = '/var/flask/MRBASEAPI/bin/activate_this.py'
execfile(activate_this,dict(__file__=activate_this))
sys.path.append('/var/flask/MRBASEAPI')
sys.path.append('/var/flask/mrbaseapi')
from api import app as liveapi
from apitest import app as testapi
# Logging
if not liveapi.debug:
    import logging
    from logging import FileHandler
    file_handler = FileHandler('/var/flask/logs/logfile.txt')
    file_handler.setLevel(logging.DEBUG)
    liveapi.logger.addHandler(file_handler)

application = DispatcherMiddleware(liveapi, {
    '/testapi':     testapi
})
