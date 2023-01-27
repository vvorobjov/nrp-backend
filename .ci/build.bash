#!/bin/bash

set -e
set -x

whoami
env | sort
pwd

# import environment
if [ -f .ci/env ]; then
    # add quotes to all vars (but do it once)
    sudo sed -i -E 's/="*(.*[^"])"*$/="\1"/' .ci/env 
    source '.ci/env'
fi

if [ -z ${PYTHON_VERSION_MAJOR_MINOR} ]; then
    export PYTHON_VERSION_MAJOR=$(python -c "import sys; print(sys.version_info.major)")
    export PYTHON_VERSION_MAJOR_MINOR=$(python -c "import sys; print('{}.{}'.format(sys.version_info.major, sys.version_info.minor))")
fi

export HBP=$WORKSPACE
cd $WORKSPACE
export PYTHONPATH=
source ${USER_SCRIPTS_DIR}/nrp_variables
# source ${USER_SCRIPTS_DIR}/nrp_aliases
cd ${EXDBACKEND_DIR}


# Configure build has to be placed before make devinstall
# export NRP_VIRTUAL_ENV=$HOME/.opt/platform_venv
export VIRTUAL_ENV=$NRP_VIRTUAL_ENV
export VIRTUAL_ENV_PATH=$VIRTUAL_ENV
# export NRP_SIMULATION_DIR=/tmp/nrp-simulation-dir
export NRP_INSTALL_MODE=dev
export PYTHONPATH=hbp_nrp_commons:hbp_nrp_backend:hbp_nrp_simserver:$VIRTUAL_ENV_PATH/lib/python${PYTHON_VERSION_MAJOR_MINOR}/site-packages:$PYTHONPATH

# version.txt
if [ -f "version.txt" ]; then sed -i -f version.txt hbp_nrp_backend/hbp_nrp_backend/version.py hbp_nrp_backend/requirements.txt; sed -i -f version.txt hbp_nrp_commons/hbp_nrp_commons/version.py hbp_nrp_commons/requirements.txt; sed -i -f version.txt hbp_nrp_simserver/hbp_nrp_simserver/version.py hbp_nrp_simserver/requirements.txt; fi

# Run tests
export IGNORE_LINT='platform_venv|ci_download_directory'
# verify_base-ci fails on dependencies mismatch, but ignores linter errors, which are caught by Jenkins afterwards
. "$VIRTUAL_ENV_PATH"/bin/activate \
        && echo "PYTHONPATH $PYTHONPATH" \
        && make verify_base-ci
