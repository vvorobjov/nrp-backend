"""
This package contains the python code to run the REST web server and supportive tooling
"""

import time

from .version import VERSION as __version__   # pylint: disable=W0611

__author__ = 'NRP software team, GeorgHinkel'


class NRPServicesGeneralException(Exception):
    """
    General exception class that can be used to return meaningful messages
    to the ExD frontend.

    :param message: message displayed to the end user.
    :param error_type: Type of error (like 'Loading Error')
    :param error_code: The HTTP error code to send to the frontend.
    """

    def __init__(self, message, error_type, error_code=500, data=None):
        super().__init__()
        # These fields are handled by the front-end code.
        self.message = message
        self.error_type = error_type
        self.error_code = error_code
        self.data = data

    def __str__(self):
        return f"{repr(self.message)} ({self.error_type})"


class NRPServicesClientErrorException(NRPServicesGeneralException):
    """
    Exception class for client (4xx) errors. It can be used to return meaningful messages
    to the ExD frontend.

    :param message: message displayed to the end user.
    :param error_code: The HTTP error code to send to the frontend.
    """

    def __init__(self, message, error_type="Client error", error_code=400):
        super().__init__(message, error_type, error_code)


class NRPServicesStateException(NRPServicesGeneralException):
    """
    State exception class that can be used to return meaningful messages to the HBP frontend.

    :param message: message displayed to the end user.
    """

    def __init__(self, message):
        super().__init__(message, "State Transition error", 400)


class NRPServicesWrongUserException(NRPServicesClientErrorException):
    """
    Exception class that can be used to return meaningful messages
    to the HBP frontend in case an invalid user is detected.

    :param message: message displayed to the end user.
    """

    def __init__(self,
                message="You need to be the simulation owner to apply your changes "
                "or the simulation should be shared with you for you to be able to access it."
                "Wrong user",):
        super().__init__(message, 401)


def get_date_and_time_string():
    """
    Utility function that returns a string reflecting the current date and time
    with a format that is suitable for file or folder names

    :return: a string containing the date and time under the format
        YYYY-mm-dd_HH-MM-SS
    """
    return '_'.join([time.strftime("%Y-%m-%d"), time.strftime("%H-%M-%S")])
