import logging
import sys

LOGGER_NAME = "mergetyp"


def configure_logging(verbose: bool, quiet: bool) -> logging.Logger:
    """Configure application logging

    Args:
        verbose: Enable debug output
        quiet: Show only errors

    Returns:
        Configured application logger
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.handlers.clear()
    logger.propagate = False

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

    if quiet:
        logger.setLevel(logging.ERROR)
        return logger

    if verbose:
        logger.setLevel(logging.DEBUG)
        return logger

    logger.setLevel(logging.INFO)
    return logger
