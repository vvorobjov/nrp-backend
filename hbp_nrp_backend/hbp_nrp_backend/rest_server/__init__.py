"""
This package contains the implementation of the REST server to control experiments
"""

__author__ = 'NRP software team, Georg Hinkel, Ugo Albanese'

from flask import Flask
from flask_smorest import Api

from hbp_nrp_backend import __version__


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

# Flask-Smorest / OpenAPI metadata. The spec is built for documentation only;
# OPENAPI_URL_PREFIX is intentionally left unset so no extra HTTP routes are
# added and the public URL surface is unchanged.
app.config['API_TITLE'] = 'NRP Backend REST API'
app.config['API_VERSION'] = __version__
app.config['OPENAPI_VERSION'] = '3.0.3'

api = Api(app)

# Import REST APIs
# pylint: disable=W0401
# importing the module will install the error handlers
import hbp_nrp_backend.rest_server.__ErrorHandlers

from .__SimulationControl import blp as simulation_control_blp
from .__SimulationService import blp as simulation_service_blp
from .__SimulationState import blp as simulation_state_blp

from .__Version import blp as version_blp

# Register /simulation and /simulation/<sim_id>[/state]
api.register_blueprint(simulation_service_blp)
# NOTE change route in case of new sim_id type
api.register_blueprint(simulation_control_blp)
api.register_blueprint(simulation_state_blp)

# Register /version
api.register_blueprint(version_blp)
