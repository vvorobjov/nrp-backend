"""
This package contains functionality shared across the NRP backend
"""
import sys
import os
import logging
from typing import Optional, Union

from .version import VERSION as __version__  # pylint: disable=W0611

__author__ = "NRP Team"



def get_python_interpreter():
    """
        When started through uWSGI, sys.executable returns the uwsgi executable and not the python
        interpreter (see https://github.com/unbit/uwsgi/issues/670 for details)
    """
    python_interpreter = sys.executable
    if python_interpreter.endswith("uwsgi") \
            or python_interpreter.endswith("uwsgi-core"):  # pragma: no cover
        # When started through uWSGI, sys.executable returns the uwsgi executable and not the python
        # interpreter (see https://github.com/unbit/uwsgi/issues/670 for details)
        home = os.environ.get('NRP_MODULE_HOME')  # TODO  NRP_MODULE_HOME ? where to set it
        if home is not None:
            # If NRP_MODULE_HOME is set, we take the python interpreter from there
            python_interpreter = os.path.join(home, "bin", "python")
        else:
            # Otherwise, we assume that the interpreter is in the PATH
            python_interpreter = "python"

    return python_interpreter


# Note that the following configuration can later be easily stored in an external
# configuration file (and then set by the user).
_log_format = '%(asctime)s [%(threadName)-12.12s] [%(name)-12.12s] [%(levelname)s]  %(message)s'


def set_up_logger(name: Optional[str] = None,
                  logfile_name: Optional[str] = None,
                  log_format:str = _log_format,
                  level: Union[int, str] = logging.INFO) -> logging.Logger:
    """
    Configure the logger named 'name'.
    If name is None, reutrn the root logger.

    :param: name: The name of the logger to be set up. 
                  None means root logger (same as logging.getLogger)
    :param: logfile_name: name of the file created to collect logs. None means stdout.
    :param: level: The logger level. Defaults to INFO.
    
    :return: the logger with the specified name configured as required.
    """
    # We initialize the logging in the startup.
    # This way we can access the already set up logger in the children modules.

    logger = logging.getLogger(name if name is not None else None)
    
    logger.setLevel(level)

    # rely on exception from FileHandler instead of checking for logfile_name not being None
    try:
        handler = logging.FileHandler(logfile_name)
    except (AttributeError, IOError, TypeError):
        handler = logging.StreamHandler(sys.stdout)
    finally:
        handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(handler)

        logger.debug("Writing logs to '%s'",
                     str(logfile_name) if isinstance(handler, logging.FileHandler) else "STDOUT")
    
    return logger
