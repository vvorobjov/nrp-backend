from nrp_core import *
from nrp_core.data.nrp_json import *


@EngineDataPack(keyword='datapack_python', id=DataPackIdentifier('datapack1', 'python_1'))
@TransceiverFunction("python_2")
def transceiver_function(datapack_python):
    rec_datapack1 = JsonDataPack("rec_datapack2", "python_2")
    for k in datapack_python.data.keys():
        rec_datapack1.data[k] = datapack_python.data[k]

    return [rec_datapack1]
