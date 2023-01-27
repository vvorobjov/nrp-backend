"""
This package controls the simulations
"""

__author__ = 'NRP software team, Georg Hinkel, Ugo Albanese'

from typing import List
import pytz

timezone = pytz.timezone('Europe/Zurich')

sim_id_type = int # before importing Simulation

from hbp_nrp_backend.simulation_control.simulation import Simulation

# the list of simulations created by this server
simulations: List[Simulation] = []

def get_simulation(sim_id: sim_id_type) -> Simulation:
    """
    Gets the simulation with the given simulation id, None otherwise

    :param sim_id: The simulation id
    :returns: The simulation object with the given sim_id, None otherwise
    :raises: ValueError When sim_id simulation doesn't exist
    """
    # NOTE change in case of different type of simulation ID
    if sim_id < 0 or sim_id >= len(simulations):
        raise ValueError
    return simulations[sim_id]

