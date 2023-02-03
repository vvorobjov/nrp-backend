"""Python Engine 1. Will get current engine time and make it accessible as a datapack"""

from nrp_core.engines.python_json import EngineScript


class Script(EngineScript):
    def initialize(self):
        """Initialize datapack1 with time"""
        print("Engine 1 is initializing. Registering datapack...")
        self._registerDataPack("datapack1")
        self._registerDataPack("actions")
        self._setDataPack("datapack1", {"time": self._time_ns, "timestep": 0 })

    def runLoop(self, timestep_ns):
        """Update datapack1 at every timestep"""
        self._setDataPack("datapack1", {"time": self._time_ns, "timestep": timestep_ns })
        print("DataPack 1 data is " + str(self._getDataPack("datapack1")))
        print("DataPack 'actions' data is " + str(self._getDataPack("actions")))

    def shutdown(self):
        print("Engine 1 is shutting down")

    def reset(self):
        print("Engine 1 is resetting")
