from redis import Redis
from rq import Queue
from data_processing.harmonise import Harmonise

q = Queue(connection=Redis())