# Download base image
ARG BASE_IMAGE=docker-registry.ebrains.eu/nrp/nrp-core/nrp-vanilla-ubuntu20:dev4.0
FROM ${BASE_IMAGE}

RUN sudo apt-get update && \
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3.8-venv python3-restrictedpython uwsgi-core uwsgi-plugin-python3 python-is-python3
RUN sudo apt-get update && \
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nginx-extras lua-cjson

WORKDIR ${HOME}/nrp-backend

COPY --chown=${NRP_USER}:${NRP_GROUP} . .

ENV NRP_INSTALL_MODE user
ENV HBP ${HOME}

ENV VIRTUAL_ENV ${HOME}/nrp-backend/platform_venv
ENV NRP_VIRTUAL_ENV VIRTUAL_ENV

RUN make devinstall

ENV VIRTUAL_ENV ${HOME}/nrp-backend/platform_venv
ENV PYTHONPATH ${PYTHONPATH}:${VIRTUAL_ENV}/lib/python3.8/site-packages
ENV PYTHONPATH $PYTHONPATH:$HBP/nrp-backend/hbp_nrp_backend:$HBP/nrp-backend/hbp_nrp_simserver:$HBP/nrp-backend/hbp_nrp_commons

ENV NRP_SIMULATION_DIR /tmp/nrp-simulation-dir
ENV STORAGE_PATH=/nrpStorage
RUN sudo mkdir -p ${STORAGE_PATH}
RUN sudo chown ${NRP_USER}:${NRP_GROUP} ${STORAGE_PATH}

CMD [ "bash", "entrypoint.sh" ]
