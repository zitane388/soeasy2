# image_tools/thumbnail_engine/logger.py

import logging

_logger = None

def get_logger():
    global _logger
    if _logger:
        return _logger

    logger = logging.getLogger("thumbnail_engine")
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        ch = logging.StreamHandler()
        fmt = logging.Formatter(
            "[%(levelname)s] %(name)s | %(message)s"
        )
        ch.setFormatter(fmt)
        logger.addHandler(ch)

    _logger = logger
    return logger
