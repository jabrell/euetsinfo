import sys

from loguru import logger


def setup_logging(level: str = "INFO"):
    """Set up logging with the specified log level."""
    logger.remove()  # remove default handler
    logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:HH:mm:ss}</green> | <level>{level:<7}</level> | <cyan>"
            "{name}</cyan> - <level>{message}</level>"
        ),
    )
