'''
Created on 25.03.2018

@author: Kevin
'''

import logging.handlers
import os
import config


# Set up a specific logger with our desired output level
log = logging.getLogger(config.LOGGER_NAME)
log.setLevel(logging.DEBUG)

# Add the log message handler to the logger
oslist = os.listdir(os.getcwd())
if "Logs" not in oslist:
    os.mkdir("Logs")
# handler = logging.handlers.TimedRotatingFileHandler(
#    config.LOG_FOLDER + config.LOG_FILENAME, when="midnight")
handler = logging.handlers.RotatingFileHandler(config.LOG_FOLDER + config.LOG_FILENAME,
                                               maxBytes=1024 * 1024, backupCount=5)
clihandler = logging.StreamHandler()
clihandler.setLevel(logging.DEBUG)
handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    '[%(asctime)s] [%(levelname)s] [%(name)s] [%(funcName)s] %(message)s')  # [%(module)s]
handler.setFormatter(formatter)
clihandler.setFormatter(formatter)
log.addHandler(handler)
log.addHandler(clihandler)
