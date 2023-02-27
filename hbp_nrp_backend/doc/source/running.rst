.. _running-backend:

Running the Backend
===================

.. todo:: Add author/responsible

Running on a local machine
--------------------------

This is a step-by-step description for running the backend for the case that **the backend is locally installed on developer a machine**.


1. Make sure you installed everything according to :ref:`installation`

2. Start the required software components such as ``roscore``, the backend server and the ``gazebo`` server. This can
   all be done using the ``runbackend`` script as decribed in :ref:`installation` or manually by:

   a. Start a roscore:

      .. code-block:: bash

         roscore

   b. Start the backend server (in a different terminal window):

      .. code-block:: bash

          python $HBP/nrp-backend/hbp_nrp_backend/hbp_nrp_backend/runserver.py

      This will start the backend server running on 127.0.0.1:5000. If you wish to run the server on another port, you have
      to provide another argument

      .. code-block:: bash

         python $HBP/nrp-backend/hbp_nrp_backend/hbp_nrp_backend/runserver.py 9000
         
   c. Start the ROSCLESimulationFactory, a ROS service needed by the backend to start an instance of the CLE

      .. code-block:: bash

         python $HBP/CLE/hbp_nrp_cle/hbp_nrp_cle/cle/ROSCLESimulationFactory.py
   d. Start the Gazebo server. Be careful that our patched Gazebo plugin is loaded instead of the default one.

      .. code-block:: bash

            source $HBP/GazeboRosPackages/devel/setup.bash
            rosrun gazebo_ros gzserver

   e. Start a Gazebo client if you wish to view the results on your machine (not required when using the Frontend)

      .. code-block:: bash

            rosrun gazebo_ros gzclient

   f. Load an experiment. The experiment configuration is the path to your experiment relative to
      $NRP_MODELS_DIRECTORY or your current folder if the first is not set

      .. code-block:: bash

            curl -X POST 127.0.0.1:5000/simulation -d '{"experimentID":"cloned_experiment_id"}'


Building the documentation
--------------------------

.. note:: The following options are available only for the core developers, who has writing access rights to the repositories and installed the NRP in developer mode: :code:`NRP_INSTALL_MODE=dev`.

General documentation and Python API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The documentation and Python API (the pages you are currently reading) is created and can be read by calling

.. code-block:: bash

    cd $EXDB/doc
    make html
    firefox build/html/index.html


Running the unit test on a local machine
----------------------------------------------------

.. note:: The following options are available only for the core developers, who has writing access rights to the repositories and installed the NRP in developer mode: :code:`NRP_INSTALL_MODE=dev`.

After downloading :ref:`installation` of the NRP and its components, you can run linting checks of the NRP Backend and related modules. 

In order to run linter-check, there is a dedicated script :code:`verify.sh`:

.. code-block:: bash

   cd $HBP/nrp-backend
   ./verify.sh #make sure it is executable

In order to tests, there is a dedicated script :code:`run_tests.sh`:

.. code-block:: bash

   cd $HBP/nrp-backend
   ./run_tests.sh #make sure it is executable
