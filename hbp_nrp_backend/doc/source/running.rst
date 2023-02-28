.. _running-backend:

Running the Backend
===================

Running on a local machine
--------------------------

This is a step-by-step description for running the backend for the case that **the backend is locally installed on developer a machine**.

.. TODO ref to installation from source

1. Make sure you installed everything according to :ref:`installation`. The following 

.. TODO ref to installation from source

2. Start the required component (i.e. the :code:`MQTT Broker` and the :code:`Storage Proxy`) refer to:  

   a. Start the backend server:

      .. code-block:: bash

         source $NRP_VIRTUAL_ENV/bin/activate
         python $HBP/nrp-backend/hbp_nrp_backend/hbp_nrp_backend/runserver.py

      This will start the backend server running on 127.0.0.1:5000. If you wish to run the server on another port, you have
      to provide another argument

      .. code-block:: bash

         source $NRP_VIRTUAL_ENV/bin/activate
         python $HBP/nrp-backend/hbp_nrp_backend/hbp_nrp_backend/runserver.py 9000
      
      .. note:: use the aliases provided by :code:`$HBP/nrp-user-scripts/nrp_aliases`: :code:`nrp-backend` and :code:`nrp-backend-verbose`. The virtual environment will be automatically activated.
   
   b. Use the :code:`NRP Frontend` to clone a template experiment and to launch it. If ID of the experiment is known in advance, requests can be sent using any REST client (e.g. Postman or curl) 


Debugging
---------

NRP Backend supports remote debugging two of the most common :abbr:`IDEs (integrated development environment)`: `Visual Studio Code <https://code.visualstudio.com>`_  and `PyCharm <https://www.jetbrains.com/pycharm/>`_.
The aliases for running NRP Backend in debug mode, provided in :code:`$HBP/nrp-user-scripts/` are :code:`nrp-backend-debug-vscode` and :code:`nrp-backend-debug-pycharm`, respectively.
When started in debug mode, NRP Backend will wait for the debugger connection on port 9991.

Below, a sample configuration from :abbr:`VScode (Visual Studio Code)`'s launch.json file is listed:

.. code-block:: json

        {
            "name": "NRP Backend: Remote Attach",
            "type": "python",
            "request": "attach",
            "subProcess": true,
            "connect": {
                "host": "localhost",
                "port": 9991
            },
            "justMyCode": false
        },


Building the documentation
--------------------------

General documentation and Python API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The documentation and Python API (the pages you are currently reading) is created by:

.. code-block:: bash

    cd $HBP/nrp-backend
    make doc # index at build/html/index.html


Unit testing
---------------

After downloading :ref:`installation` of the NRP and its components, you can run linting checks of the NRP Backend and related modules. 

In order to run linter-check, there is a dedicated script :code:`verify.sh`:

.. code-block:: bash

   cd $HBP/nrp-backend
   ./verify.sh #make sure it is executable

In order to tests, there is a dedicated script :code:`run_tests.sh`:

.. code-block:: bash

   cd $HBP/nrp-backend
   ./run_tests.sh #make sure it is executable
