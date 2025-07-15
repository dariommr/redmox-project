"""
    Module providing common functions for every tool
"""

#!/usr/bin/env python3

import os
import sys
import logging
import socket

class Clr:
    """
        Managing colors class
    """
    green = "\033[0;32m"
    yellow = "\033[1;33m"
    red = "\033[0;31m"
    purple = "\033[0;35m"
    black = "\033[0;30m"
    brown = "\033[0;33m"
    blue = "\033[0;34m"
    cyan = "\033[0;36m"
    light_gray = "\033[0;37m"
    dark_gray = "\033[1;30m"
    light_red = "\033[1;31m"
    light_green = "\033[1;32m"
    light_blue = "\033[1;34m"
    light_purple = "\033[1;35m"
    light_cyan = "\033[1;36m"
    light_white = "\033[1;37m"
    bold = "\033[1m"
    faint = "\033[2m"
    italic = "\033[3m"
    underline = "\033[4m"
    blink = "\033[5m"
    negative = "\033[7m"
    crossed = "\033[9m"
    reset = "\033[0m"

class CustomFormatter(logging.Formatter):
    """
        Class to set the format for logs
    """
    hostname = socket.gethostname()
    header = f'%(asctime)s %(name)s'
    FORMATS = {
        logging.DEBUG: f'{header}: [%(levelname)s] %(message)s',
        logging.INFO: f'{header}: {Clr.green}[%(levelname)s]{Clr.reset} %(message)s',
        logging.WARNING: f'{header}: {Clr.yellow}[%(levelname)s]{Clr.reset} %(message)s',
        logging.ERROR: f'{header}: {Clr.red}[%(levelname)s]{Clr.reset} %(message)s',
        logging.CRITICAL: f'{header}: {Clr.purple}[%(levelname)s]{Clr.reset} %(message)s'
    }
    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

def set_logger(name, logfile=None, debug=False):
    """
    Function to set a logger
    """

    main_logger = logging.getLogger(name)
    if debug:
        main_logger.setLevel(logging.DEBUG)
    else:
        main_logger.setLevel(logging.INFO)

    if logfile:
        file_handler = logging.FileHandler(logfile)
        file_handler.setFormatter(CustomFormatter())
        main_logger.addHandler(file_handler)
    else:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(CustomFormatter())
        main_logger.addHandler(stream_handler)

    return main_logger
