import logging
import os


def initialise_from_env():
    logging_level = os.getenv('LOGGING_LEVEL', 'INFO')

    logging.basicConfig(level=logging.getLevelName(logging_level))
