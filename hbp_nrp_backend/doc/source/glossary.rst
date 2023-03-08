Glossary
*********

.. Glossary::

    NRP
        The HBP Neurobotics Platform.

    Simulation Server
        The component of NRP Backend that runs :code:`nrp-core` based python script driving a simulated experiment.

    MQTT
        "MQ Telemetry Transport or Message Queue Telemetry Transport" is a lightweight, publish-subscribe, machine to machine network protocol for message queue/message queuing service.
        In the NRP is used for inter- (:code:`NRP Backend`, :code:`nrp-core` -> :code:`NRP Frontend`) and intra- (:ref:`rest-server` <-> :ref:`simulation-server`) component communication.