#!/bin/bash
# This script is designed for local usage.

# Note: Dont put CLE into this list. otherwiese the files CLELauncher, ROSCLEServer and others will not be pep8 and pylint validated!
export IGNORE_LINT="platform_venv|hbp_nrp_commons/hbp_nrp_commons/generated|migrations|build"
export VIRTUAL_ENV=$NRP_VIRTUAL_ENV


# This script only runs static code analysis, the tests can be run separately using run_tests.sh
make run_pycodestyle run_pylint
RET=$?

if [ $RET == 0 ]; then
    echo -e "\033[32mVerify sucessfull.\e[0m Run ./run_tests.sh to run the tests."
else
    echo -e "\033[31mVerify failed.\e[0m"
fi

exit $RET
