import logging
import logging.config
import os


class NoPymongoDebugFilter(logging.Filter):
    """Filter out very chatty pymongo debug messages."""
    def filter(self, record: logging.LogRecord) -> bool:
        # Drop pymongo debug-level records
        if record.name.startswith("pymongo") and record.levelno <= logging.DEBUG:
            return False
        return True


def configure_logging():
    """Centralized logging configuration.

    - Sets sensible root log level (overridable with LOG_LEVEL env)
    - Routes logs to stdout with a compact formatter
    - Quiet noisy third-party loggers (pymongo, urllib3, google_genai, werkzeug)
    - Adds a small filter to drop debug pymongo noise if it appears
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s %(levelname)4s %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
        "filters": {
            "no_pymongo_debug": {
                "()": NoPymongoDebugFilter
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "level": log_level,
                "filters": ["no_pymongo_debug"],
                "stream": "ext://sys.stdout",
            }
        },
        "root": {
            "handlers": ["console"],
            "level": log_level,
        },
        "loggers": {
            # Very chatty libraries we generally don't need at DEBUG
            "pymongo": {"level": "WARNING", "handlers": ["console"], "propagate": False},
            "urllib3": {"level": "WARNING", "handlers": ["console"], "propagate": False},
            "google_genai": {"level": "WARNING", "handlers": ["console"], "propagate": False},
            "google": {"level": "WARNING", "handlers": ["console"], "propagate": False},
            "werkzeug": {"level": "ERROR", "handlers": ["console"], "propagate": False},
        },
    }

    logging.config.dictConfig(config)


__all__ = ["configure_logging"]
