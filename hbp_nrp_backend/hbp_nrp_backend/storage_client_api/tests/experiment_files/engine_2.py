"""Python Engine 2. Will get time from Engine 1 and print it"""

from nrp_core.engines.python_json import EngineScript

class Script(EngineScript):
    def initialize(self):
        """Initialize datapack1 with empty time"""
        print("Engine 2 is initializing. Registering datapack...")
        self._registerDataPack("rec_datapack2")
        self._setDataPack("rec_datapack2", { "time" : self._time_ns, "timestep": 0 })

    def runLoop(self, timestep_ns):
        """Receive datapack1 at every timestep"""
        dev1 = self._getDataPack("rec_datapack2")
        print("Engine 2 received data is " + str(dev1))

    def shutdown(self):
        print("Engine 2 is shutting down")
