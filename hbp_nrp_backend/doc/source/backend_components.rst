======================
NRP Backend Components
======================

.. todo:: Add author/responsible


.. _rest-server:

REST Server
++++++++++++++++++++

The REST Server implemented in the package ::code:`hbp_nrp_backend`.
It takes care of exposing the execution of npr-core based experiment as REST resources.
It leverages the `Flask <https://flask.palletsprojects.com/>`_  and `Flask-Restful <https://flask-restful.readthedocs.io>`_ frameworks
to implement REST Services that can create, manage, and stop experiments (see :ref:`backend-rest-api`).

One of its responsibilities is to manage the local execution environment in the context of which the :code:`Simulation Server` will run the experiment.
When serving an experiment launching request, it takes care of fetching the experiment data from the :code:`Storage Server`, for the use of the :code:`Simulation Server`.
Once the simulation has successfully (or unsuccessfully) terminated, it upload the simulation logs to the :code:`Storage Server` for the user to inspect.

Another responsibility is, once having prepared the execution environment, to spawn a :code:`Simulation Server` that will execute the nrp-core based simulation script controlling the requested experiment.

The sequence diagram :numref:`launch-experiment-backend`, depicts such processes.

.. _launch-experiment-backend:
.. image:: img/launch_experiment_backend.png
   :width: 100%

   Experiment launching (REST Server)


.. _simulation-server:

In the REST Server, the lifecycle of an experiment simulation is governed by an instance of :code:`SimulationLifecycle`; in particular, by its specialization  :code:`BackendSimulationLifecycle`.
For details see the relative section ( TODO LINK) of this manual.

Simulation Server
++++++++++++++++++++

The purpose of the Simulation Server is to run nrp-core based python scripts from a local directory prepared by the :ref:`rest-server`.
When the launching of an experiment is requested, it gets spawned, as sub process, by the :ref:`rest-server`.
It, then, loads and executes the experiment script (e.g. main_script.py) until completion or user request of stopping it. While running, the execution can be paused.

.. note:: The Simulation Sever can pause and stop the execution of nrp-core based python script; i.e. python scripts with the following structure. It is required to use the function :code:`nrp.run_loop` to loop over simulation timesteps or until the exception :code:`NRPSimulationTimeout` is raised.

.. literalinclude:: img/main_script.py
   :linenos:
   :name: main_script.py

The execution can be controlled because any programmatic interaction with nrp-core python client (i.e. :code:`nrp_core.client.NrpCore`) is mediated by the class :code:`NRPCoreWrapper`.
This class wraps an instance of :code:`NrpCore` intercepting any call and, before forwarding the call to the wrapped instance, it performs all the required management tasks (e.g. time keeping, checking whether pause or stop has been requested).

The lifecycle a Simulation Server is governed by an instance of :code:`SimulationLifecycle`, in particular by its specialization :code:`SimulationServerLifecycle`.
For details see the relative section of this manual.

.. Frontend
.. --------

.. The Frontend basically calls the REST API of the backend via HTTP using JSON for data transfer. For rendering the Frontend can directly access the Gazebo API running in the CLE by using gzweb/gz3d. In addition the Frontend subscribes to ROS topics in the CLE for status updates (*/ros_cle_simulation/status*) and monitoring brain/robot activities (*/monitoring/'device_type'*) by using rosbridge.

.. Backend
.. -------

.. The REST Server uses the classes :class:`hbp_nrp_backend.cle_interface.ROSCLESimulationFactoryClient` and :class:`hbp_nrp_backend.cle_interface.ROSCLEClient` to start and control the CLE. Both classes communicate with their counter part in the CLE by calling ROS services (*/ros_cle_simulation/create_new_simulation*) to launch the CLE and (*/ros/cle_simulation/{start,stop,pause,reset,stop}*) to control the CLE.
.. In addition the backend is able to call ROS services of Gazebo (*/gazebo/{light,visual}*) to perform events and interactions with the environment of the simulation.

.. Closed Loop Engine
.. ------------------

.. The CLE internal communication is basically done via ROS services and topics. See :ref:`CLE documentation <cle-developer-manual>` for more details.

