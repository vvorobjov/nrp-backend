# Download base image. Defaults to the nest-gazebo nrp-core variant
# (the one most templates need); the GitHub Actions workflow overrides
# this per variant via --build-arg BASE_IMAGE=hbpneurorobotics/nrp-<variant>.
ARG BASE_IMAGE=hbpneurorobotics/nrp-nest-gazebo:latest
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

# nginx is started by entrypoint.sh and listens on 8090 (per the
# nrp-user-scripts/config_files/nginx.docker/conf.d/nrp-services.conf
# that gets mounted in). /version is an unauthenticated Flask-RESTful
# resource (api.add_resource(Version, '/version')), suitable for a
# liveness probe. `localhost` resolves to both 127.0.0.1 and ::1 via
# /etc/hosts, so the probe survives an IPv6-only bind.
ENV BACKEND_HEALTHCHECK_URL=http://localhost:8090/version
HEALTHCHECK --interval=20s --timeout=5s --start-period=60s --retries=3 \
  CMD python3 -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen(__import__('os').environ['BACKEND_HEALTHCHECK_URL'], timeout=4).status < 500 else 1)" \
      || exit 1

CMD [ "bash", "entrypoint.sh" ]
