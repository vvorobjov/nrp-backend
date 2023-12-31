##
## Target All Components in Package by Default (e.g. make verify)
##

#modules that have tests
TEST_MODULES=hbp_nrp_commons/hbp_nrp_commons/ hbp_nrp_backend/hbp_nrp_backend/ hbp_nrp_simserver/hbp_nrp_simserver/

#modules that are installable (ie: ones w/ setup.py)
INSTALL_MODULES=hbp_nrp_commons hbp_nrp_backend hbp_nrp_simserver

#packages to cover
COVER_PACKAGES=hbp_nrp_commons,hbp_nrp_backend,hbp_nrp_simserver

#documentation to build
DOC_MODULES=hbp_nrp_commons/doc hbp_nrp_backend/doc hbp_nrp_simserver/doc

PYTHON_PIP_VERSION?=pip>=19

##
## Individual Component Release Targets
##
verify-hbp_nrp_commons:
	$(MAKE) verify TEST_MODULES=hbp_nrp_commons/hbp_nrp_commons/\
                       INSTALL_MODULES=hbp_nrp_commons\
                       COVER_PACKAGES=hbp_nrp_commons\
                       DOC_MODULES=hbp_nrp_commons/doc/\
                       IGNORE_LINT="$(IGNORE_LINT)|hbp_nrp_simserver|hbp_nrp_backend"

##### DO NOT MODIFY BELOW #####################

include user_makefile
