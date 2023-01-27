'''setup.py'''
from builtins import next

import os

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup  # pylint:disable=no-name-in-module, import-error

import pip
from optparse import Option  # pylint:disable=deprecated-module

import hbp_nrp_simserver


def parse_reqs(reqs_file):
    """ parse the requirements """
    return list(val.strip() for val in open(reqs_file))

BASEDIR = os.path.dirname(os.path.abspath(__file__))
REQS = parse_reqs(os.path.join(BASEDIR, 'requirements.txt'))

# ensure we install numpy before the main list of requirements, ignore
# failures if numpy/cython are not requirements and just proceed (futureproof)
try:
    cython_req = next(r for r in REQS if r.startswith('cython'))
    numpy_req = next(r for r in REQS if r.startswith('numpy'))
    pip.main(['install', '--no-clean', cython_req, numpy_req])  # pylint:disable=no-member
except Exception:  # pylint: disable=broad-except
    pass

EXTRA_REQS_PREFIX = 'requirements_'
EXTRA_REQS = {}
for file_name in os.listdir(BASEDIR):
    if not file_name.startswith(EXTRA_REQS_PREFIX):
        continue
    base_name = os.path.basename(file_name)
    (extra, _) = os.path.splitext(base_name)
    extra = extra[len(EXTRA_REQS_PREFIX):]
    EXTRA_REQS[extra] = parse_reqs(file_name)

config = {
    'description': 'A server for nrp-core simulations',
    'author': 'HBP Neurorobotics',
    'url': 'http://neurorobotics.net',
    'author_email': 'neurorobotics-support@humanbrainproject.eu',
    'version': hbp_nrp_simserver.__version__,
    'install_requires': REQS,
    'extras_require': EXTRA_REQS,
    'COMPONENTS_PACKAGES_NAMES': ['hbp_nrp_simserver',
                            'hbp_nrp_simserver.server'],
    'package_data': {
        'hbp_nrp_simserver.bibi_config': ['tf_template.pyt']
    },
    'classifiers': ['Programming Language :: Python :: 3'],
    'scripts': [],
    'name': 'hbp-nrp-simserver',
    'include_package_data': True,
}

setup(**config)
