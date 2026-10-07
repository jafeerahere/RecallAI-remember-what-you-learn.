import logging
from logging.handlers import RotatingFileHandler
from utils.config import data_dir

def get_logger():
    logger = logging.getLogger('recallai')
    if not logger.handlers:
        try:
            path = data_dir()
            path.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(path / 'application.log', maxBytes=2_000_000, backupCount=2, encoding='utf-8')
            handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
            logger.addHandler(handler)
        except OSError:
            logger.addHandler(logging.StreamHandler())
        logger.setLevel(logging.INFO)
    return logger
