'''version string - automatically calculated from the SCM (git).

Resolution order (EBR2-55):
  1. ``NRP_BACKEND_VERSION`` env var, if set and non-empty.
  2. ``$HBP/nrp-user-scripts/nrp_get_scm_version.sh get_scm_version``,
     if reachable. This is the historic path used in the source
     install where nrp-backend lives next to nrp-user-scripts.
  3. Sentinel ``0.0.0+unknown`` so the package still imports in
     environments that don't have nrp-user-scripts on disk (e.g. the
     Bitbucket Pipelines build context, which only checks out
     nrp-backend).
'''
import os
import subprocess
from subprocess import CalledProcessError

_FALLBACK_VERSION = '0.0.0+unknown'


def _from_env():
    v = os.getenv('NRP_BACKEND_VERSION', '').strip()
    return v or None


def _from_scm_script():
    hbp = os.getenv('HBP')
    if not hbp:
        return None
    script = os.path.join(hbp, 'nrp-user-scripts', 'nrp_get_scm_version.sh')
    if not os.path.isfile(script):
        return None
    try:
        out = subprocess.run(
            ['bash', script, 'get_scm_version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        ).stdout.decode('utf-8').strip()
    except (CalledProcessError, FileNotFoundError, OSError):
        return None
    return out or None


def _get_version():
    return _from_env() or _from_scm_script() or _FALLBACK_VERSION


VERSION = _get_version()
