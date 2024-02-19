import logging


def setup_logging(level):
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s')
    logging.getLogger('dothttp').setLevel(level)
    logging.getLogger('request').setLevel(level)
    logging.getLogger('curl').setLevel(level)
