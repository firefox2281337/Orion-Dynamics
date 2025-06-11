import logging
import sys

def setup_logger(log_level=logging.INFO):

    logger = logging.getLogger('app_logger')
    logger.setLevel(log_level)

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    file_handler   = logging.FileHandler('app.log', encoding='utf-8')

    log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s')

    file_handler.setFormatter(log_format)

    logger.addHandler(file_handler)

    return logger