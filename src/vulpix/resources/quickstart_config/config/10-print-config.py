"""
this script is an example that demonstrates how your scripts can access the config
stored in your blueprint.
"""

import logging
from typing import Any


def main(config: Any, logger: logging.Logger):
    logger.info("below is your 'scripts' config (UwU)!")
    logger.info(str(config))
