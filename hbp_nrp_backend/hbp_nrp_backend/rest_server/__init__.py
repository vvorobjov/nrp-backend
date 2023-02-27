"""
This package contains the implementation of the REST server to control experiments
"""

__author__ = 'NRP software team, Georg Hinkel, Ugo Albanese'

from flask import Flask
from flask_restful import Api


def docstring_parameter(*sub):
    """
    Helper functions to include variables in docstrings using the @docstring_parameter decorator

    :param sub: List of variables to be included in the docstring.
    """

    def dec(obj):
        """
        Reformat docstring with variables.
        """
        try:
            obj.__doc__ = obj.__doc__.format(*sub)
        except IndexError as e:
            raise IndexError(
                f"No match in templated docstring of {obj.__module__}.{obj.__name__}") from e
        return obj

    return dec


class NRPServicesExtendedApi(Api):
    """
    Extend Flask Restful error handling mechanism so that we can still use original Flask error
    handlers (defined in __ErrorHandlers.py)
    """

    def error_router(self, original_handler, e):
        """
        Route the error

        :param original_handler: Flask handler
        :param e: Error
        """
        return original_handler(e)


class ErrorMessages:
    """
    Definition of error strings
    """
    SERVER_ERROR_500 = "The query failed due to an internal server error"

    SIMULATION_NOT_FOUND_404 = "The simulation with the given ID was not found"

    OPERATION_INVALID_IN_CURRENT_STATE_403 = "The operation is forbidden while the simulation is " \
                                             "in its current state"

    SIMULATION_PERMISSION_401_VIEW = "Insufficient permissions to see the simulation changes. " \
                                     "You can only see the simulations you own or those for which " \
                                     "the experiment has been shared with you"
    SIMULATION_PERMISSION_401 = "Insufficient permissions to apply changes. Operation only allowed" \
                                " by simulation owner"
    SIMULATION_RETRIEVED_200 = "Simulation retrieved successfully"
    SIMULATIONS_RETRIEVED_200 = "Simulations retrieved successfully"
    SIMULATION_CREATED_201 = "Simulation created successfully"
    SIMULATION_ANOTHER_RUNNING_409 = "Another simulation is already running on the server"

    INVALID_STATE_TRANSITION_400 = "The state transition is invalid"
    STATE_APPLIED_200 = "Success. The new state has been correctly applied"
    STATE_RETRIEVED_200 = "Success. The simulation state has been retrieved"

    VERSIONS_RETRIEVED_200 = "Success. Components versions has been retrieved"


app = Flask(__name__, static_folder='')
api = NRPServicesExtendedApi(app)

# Import REST APIs
# pylint: disable=W0401
# importing the class will install the handlers
import hbp_nrp_backend.rest_server.__ErrorHandlers

from .__SimulationControl import SimulationControl
from .__SimulationService import SimulationService
from .__SimulationState import SimulationState

from .__Version import Version

# Register /simulation
api.add_resource(SimulationService, '/simulation')
 # NOTE change in case of new sim_id type
api.add_resource(SimulationControl, '/simulation/<int:sim_id>')
api.add_resource(SimulationState, '/simulation/<int:sim_id>/state')

# Register /version
api.add_resource(Version, '/version')
