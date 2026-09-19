from logging import (
    Logger,
    basicConfig,
    getLogger,
    Formatter,
    WARNING,
    DEBUG,
    INFO,
    CRITICAL,
    ERROR,
)
import sys


def setup_logging(logger: Logger = getLogger(), log_level: int = WARNING) -> Logger:
    """
    Configures the root logger with a specified level, format, and date format.

    Args:
        log_level: The minimum logging level to capture. Defaults to logging.WARNING.
    """
    format_str = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    formatter = Formatter(format_str)
    basicConfig(
        level=log_level,
        format=format_str,
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
    if not logger.handlers:
        for handler in getLogger().handlers:
            handler.setFormatter(formatter)
            handler.setLevel(log_level)
        for handler in logger.handlers:
            handler.setFormatter(formatter)
            handler.setLevel(log_level)
    logger.setLevel(log_level)
    return logger
