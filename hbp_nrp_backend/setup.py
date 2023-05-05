"""setup.py"""
from builtins import next

from setuptools import setup

import hbp_nrp_backend

reqs_file = './requirements.txt'

reqs = list(val.strip() for val in open(reqs_file))

config = {
    'description': 'REST Backend for nrp-core',
    'author': 'HBP Neurorobotics',
    'url': 'http://neurorobotics.net',
    'author_email': 'neurorobotics-support@humanbrainproject.eu',
    'version': hbp_nrp_backend.__version__,
    'install_requires': reqs,
    'COMPONENTS_PACKAGES_NAMES': ['hbp_nrp_backend',
                                  'hbp_nrp_backend.rest_server',
                                  'hbp_nrp_backend.storage_client_api',
                                  'hbp_nrp_backend.simulation_control'],
    'classifiers': ['Programming Language :: Python :: 3'],
    'scripts': [],
    'name': 'hbp_nrp_backend',
    'include_package_data': True,
}

setup(**config)
