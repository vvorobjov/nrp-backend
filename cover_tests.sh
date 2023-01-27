testnrp() {
    local ROOTDIR=$(git rev-parse --show-toplevel 2>/dev/null)
    if [[ $? -ne 0 ]]; then
        echo "Not in a git repository, exiting."
        return 1;
    fi
 
    if [ "$ROOTDIR" == "$EXDB" ]; then
        pushd $ROOTDIR
        . platform_venv/bin/activate
        nosetests -v hbp_nrp_backend/hbp_nrp_backend -e functional_tests --exe --with-timer \
            --with-coverage --cover-inclusive --cover-package="hbp_nrp_backend" \
            --with-xunit --xunit-file="test-reports/nosetests_hbp_nrp_backend.xml" \
            --cover-html --cover-html-dir="html_backend";
        nosetests -v hbp_nrp_simserver/hbp_nrp_simserver -e functional_tests --exe --with-timer \
            --with-coverage --cover-inclusive --cover-package="hbp_nrp_simserver" \
            --with-xunit --xunit-file="test-reports/nosetests_hbp_nrp_simserver.xml" \
            --cover-html --cover-html-dir="html_cleserver";
        nosetests -v hbp_nrp_commons/hbp_nrp_commons -e functional_tests --exe --with-timer \
            --with-coverage --cover-inclusive --cover-package="hbp_nrp_commons" \
            --with-xunit --xunit-file="test-reports/nosetests_hbp_nrp_commons.xml" \
            --cover-html --cover-html-dir="html_commons";
        deactivate
        firefox html_backend/index.html
        firefox html_cleserver/index.html
        firefox html_commons/index.html
        popd
    else
        echo "I don't know what to do with this repo. Farewell."
    fi
 
    return 0;

    }
