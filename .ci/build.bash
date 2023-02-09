#!/bin/bash

set -e
set -x

whoami
env | sort
pwd

apt update && apt install -y python-is-python3 python3.8-venv

export PYTHON_VERSION_MAJOR=$(python -c "import sys; print(sys.version_info.major)")
export PYTHON_VERSION_MAJOR_MINOR=$(python -c "import sys; print('{}.{}'.format(sys.version_info.major, sys.version_info.minor))")

export HBP=$WORKSPACE
cd $WORKSPACE/${NRPBACKEND_DIR}

export NRP_SIMULATION_DIR=/tmp/nrp-simulation-dir
export NRP_VIRTUAL_ENV=$HBP/platform_venv
export VIRTUAL_ENV=$NRP_VIRTUAL_ENV

export PYTHONPATH=hbp_nrp_commons:hbp_nrp_backend:hbp_nrp_simserver:$VIRTUAL_ENV_PATH/lib/python${PYTHON_VERSION_MAJOR_MINOR}/site-packages:$PYTHONPATH
export PYTHONPATH=$NRP_INSTALL_DIR/lib/python${PYTHON_VERSION_MAJOR_MINOR}/site-packages:$PYTHONPATH
export PYTHONPATH=$NRP_DEPS_INSTALL_DIR/lib/python${PYTHON_VERSION_MAJOR_MINOR}/site-packages:$PYTHONPATH

# version.txt
if [ -f "version.txt" ]; then sed -i -f version.txt hbp_nrp_backend/hbp_nrp_backend/version.py hbp_nrp_backend/requirements.txt; sed -i -f version.txt hbp_nrp_commons/hbp_nrp_commons/version.py hbp_nrp_commons/requirements.txt; sed -i -f version.txt hbp_nrp_simserver/hbp_nrp_simserver/version.py hbp_nrp_simserver/requirements.txt; fi

# Run tests
export IGNORE_LINT='platform_venv|ci_download_directory'
# verify_base-ci fails on dependencies mismatch, but ignores linter errors, which are caught by Jenkins afterwards
make verify_base-ci
