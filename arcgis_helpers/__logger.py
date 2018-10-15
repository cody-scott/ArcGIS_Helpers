import logging
from logging.config import dictConfig

# _logger = logging.getLogger()
# handler = logging.StreamHandler()
# formatter = logging.Formatter(
#         '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
# handler.setFormatter(formatter)
# _logger.addHandler(handler)
# _logger.setLevel(logging.INFO)


_logging_config = dict(
    version = 1,
    formatters = {
        'f': {'format':
              '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'}
        },
    handlers = {
        'h': {'class': 'logging.StreamHandler',
              'formatter': 'f',
              'level': logging.DEBUG}
        },
    root = {
        'handlers': ['h'],
        'level': logging.DEBUG,
        },
)

dictConfig(_logging_config)
_logger = logging.getLogger()
_logger.setLevel(logging.INFO)