import logging
import sys
from app.core.config import settings

def setup_logger():
    logger = logging.getLogger("app")
    logger.setLevel(settings.LOG_LEVEL)

    # Use stdout
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

logger = setup_logger()
