'''version string - automatically calculated from the SCM (git)'''
import subprocess
import os
from subprocess import CalledProcessError

def _get_version():
    try:
        version = subprocess.run(['bash',
                            f'{os.getenv("HBP")}/nrp-user-scripts/nrp_get_scm_version.sh',
                            'get_scm_version'],
                            stdout=subprocess.PIPE, check=True).stdout.decode('utf-8')
    except CalledProcessError as e:
        raise RuntimeError("The SCM version calculation script failed.\
            Expected path: $HBP/nrp-user-scripts/nrp_get_scm_version.sh,\
            check its existance.") from e
    return version

VERSION = _get_version()
