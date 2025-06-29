import logging
import utility as util
import time
import os

global_logger = logging.getLogger("Youtify")
current_date = time.ctime(time.time()).replace(':', '-')
log_filename = (os.path.join(util.LOG_LOCATION, current_date) + '.log')
with open(log_filename, 'w'):
  logging.basicConfig(filename=log_filename, level=logging.DEBUG)
global_logger.setLevel(logging.DEBUG)