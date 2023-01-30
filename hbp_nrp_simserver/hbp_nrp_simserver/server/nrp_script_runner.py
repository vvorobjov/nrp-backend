# ---LICENSE-BEGIN - DO NOT CHANGE OR MOVE THIS HEADER
# This file is part of the Neurorobotics Platform software
# Copyright (C) 2014,2015,2016,2017 Human Brain Project
# https://www.humanbrainproject.eu
#
# The Human Brain Project is a European Commission funded project
# in the frame of the Horizon2020 FET Flagship plan.
# http://ec.europa.eu/programmes/horizon2020/en/h2020-section/fet-flagships
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
# ---LICENSE-END
"""
This module contains the start script of a state machine process
"""
import ast
import contextlib
import logging
import sys
import os
import threading
import traceback
from typing import Optional, Callable, List

from hbp_nrp_commons import set_up_logger
import hbp_nrp_simserver.server.experiment_configuration as exp_conf
import hbp_nrp_simserver.server as simserver
import hbp_nrp_simserver.server.nrp_core_wrapper as nrp_core_wrapper
from hbp_nrp_simserver.server.nrp_core_wrapper import NRPSimulationTimeout, NRPStopExecution


__author__ = 'NRP software team, Ugo Albanese'

logger = logging.getLogger(__name__)

NRP_CORE_MODULES_NAMES = ["nrp_core, nrp_core.client"]

# maximum waiting time in secs for the joining of the main user script thread
MAX_STOP_TIMEOUT: float = 20.


class NRPScriptRunner:
    """
    Executes nrp-core experiments "main script" as a python script.
    
    The script excecution can be started, paused and stopped.
    The script is expected to use the injected 'nrp' handler
    (an instance of NRPCoreWrapper) and call its run_loop method
    until a NRPSimulationTimeout is raised.
    """
    def __init__(self,
                 sim_settings: simserver.SimulationSettings,
                 exp_config: exp_conf.type_class,
                 publish_error: Callable[..., None]):
        """
        :param sim_settings: the settings of the running simulation
        :param exp_config: A parsed experiment configuration with attribute-accessible elements
                           (e.g. experiment_configuration.type_class)
        :param publish_error: a function for error publishing
        """
        self.sim_settings = sim_settings
        self.exp_config = exp_config
        self._publish_error = publish_error

        self.script_path: str = sim_settings.main_script_file
        self.sim_id: str = sim_settings.sim_id

        self.script_source: str = ""

        # instance of a wrapped nrp_core client, created in self.initialize()
        self.__nrp_core_wrapped: Optional[nrp_core_wrapper.NrpCoreWrapper] = None

        self.__exec_thread: Optional[threading.Thread] = None

        # started event: signals __exec_thread to start 
        # set in start() cleared in pause()
        self.__exec_started_event: threading.Event = threading.Event()
        # started event: signals __exec_thread to stop
        # set once in stop(). Never cleared
        self.__exec_stopped_event: threading.Event = threading.Event() # one-shot. Never cleared

        # set up logger for the script to use
        self.__script_logger: logging.Logger = self._set_up_script_logger()


    def _set_up_script_logger(self) -> logging.Logger:
        """
            Sets the script logger up.

            Scripts will be able to log to the log file named script_file_name.log
            Default level is DEBUG, it can be chenged from the script.
            Log messages won't be propagated to the parent loggers (likely outputting to STOUT).
            
            :return: The script logger set up as described abose.
        """

        script_file_name, _ext = os.path.splitext(os.path.basename(self.script_path))

        script_logger = set_up_logger(name=f"{__name__}.{script_file_name}",
                            logfile_name=f"{script_file_name}_{self.sim_id}.log",
                            log_format=None, # TODO script logger format?
                            level=logging.DEBUG)

         # don't propagate to parent loggers (i.e. write only in the log file)
        script_logger.propagate = False

        return script_logger

    @property
    def simulation_time_remaining(self) -> float:
        return self.__nrp_core_wrapped.simulation_time_remaining if self.is_initialized else 0.

    @property
    def simulation_time(self) -> float:
        return self.__nrp_core_wrapped.simulation_time if self.is_initialized else 0.

    @property
    def real_time(self) -> float:
        return self.__nrp_core_wrapped.real_time if self.is_initialized else 0.

    @property
    def is_initialized(self) -> Optional[bool]:
        return self.__nrp_core_wrapped is not None

    def initialize(self) -> None:
        """
        Initialize the script runner:
        - read the script
        - initialize the (wrapped) nrp_core client

        Any nrp_core client initialization error will be raised.

        It gets called by whatever component is controlling the simulation
        (i.e. a SimulationServerLifecycle)

        :raises: IOError when the script can't be read from the file system
        :raises: SyntaxError when the script code has such an error
        """

        # called by lifecycle initialize method
        logger.info("Loading '%s' code. Simulation ID '%s'", self.script_path, self.sim_id)

        self.script_source = self.__validate_script_syntax(self.__read_script_source())

        try:
            # initialize nrp_core_wrapper.NrpCoreWrapper instance
            # any nrp_core client issue with initialization will raise
            self.__nrp_core_wrapped = \
                nrp_core_wrapper.NrpCoreWrapper(simserver.NrpCoreClientClass,
                                                self.sim_id,
                                                self.sim_settings.exp_config_file,
                                                self.exp_config,
                                                self.__exec_started_event,
                                                self.__exec_stopped_event)
            self.__nrp_core_wrapped._initialize()
        
        except Exception as e:  # pylint:disable=broad-except
            self._publish_error(msg=f"Error initializing nrp_core client. Check logs. "
                                    f"Simulation ID {self.sim_id}: {str(e)}",
                                error_type="Loading")
            raise

    def __read_script_source(self) -> str:
        try:
            with open(self.script_path) as f:
                return f.read()
        except IOError as e:  # pylint:disable=broad-except
            self._publish_error(msg=f"Error loading main script : {str(e)}",
                                error_type="Loading")
            raise

    def __validate_script_syntax(self, script_source) -> str:
        """
        :return: script_source if valid, raises otherwise
        :raise: SyntaxError if script_source fail syntax analysis
        """
        try:
            # TODO script_source can be anything. how to check its validity as a NrpCore script?
            ast.parse(script_source)  # check syntax
        except SyntaxError as e:
            self._publish_error(msg=f"SyntaxError in (Line {e.lineno}): {str(e)}",
                                error_type="Compile", line_number=e.lineno,
                                offset=e.offset, line_text=e.text)
            raise
        else:
            return script_source

    def __execute_script(self, completed_callback: Callable[[], None] = lambda: None) -> None:
        """
        Executes the user script in a new global environment in which
        self.__nrp_core_wrapped is bound to a variable named 'nrp'.
        In case of any error raised by the execution of self.script_source, an error message is sent
        using self._publish_error.

        The function waits on self.__exec_stopped_event being set,
        i.e. when the script runner (self) is requested to stop the execution calling self.stop()
        """
        # pylint: disable=broad-except
        logger.info(f"[ID {self.sim_id}] Executing main script")
        
        # NOTE Add here any name that should be available to the running script
        script_global_env = {"NRPSimulationTimeout": NRPSimulationTimeout,
                             "nrp": self.__nrp_core_wrapped,
                             "file_logger": self.__script_logger,
                             "logging": logging
                            }

        try:
            with self._hide_modules(NRP_CORE_MODULES_NAMES):
                exec(self.script_source, script_global_env)

        except (AttributeError, NameError, SyntaxError) as e:
            try:
                cl, _, tb = sys.exc_info()
                error_class = f"{cl.__name__}"
                lineno = traceback.extract_tb(tb)[-1][1]

                self._publish_error(msg=f"{error_class} in main script (Line {lineno}): {str(e)}",
                    error_type="Compile",
                    line_number=lineno)
            finally:
                del tb  # as recommended in the docs
        except NRPStopExecution:
            # The script execution has been stopped before its natural termination
            # It's been requested, so it's not an error, don't publish
            logger.info("Exiting main script thread. Simulation ID '%s'", self.sim_id)
        except NRPSimulationTimeout as e:
            logger.info("%s. Simulation ID '%s'", str(e), self.sim_id)
            self._publish_error(msg=str(e), error_type="SimTimeout")
        except Exception as e:
            logger.exception("%s. Simulation ID '%s'", str(e), self.sim_id)
            self._publish_error(msg=str(e), error_type="Runtime")
        finally:
            # main script exectution completed
            completed_callback()


    def start(self, completed_callback: Callable[[], None] = lambda: None) -> None:
        """
        Starts the script
        :param: completed_callback: A callable to be called when the main script
                                    has terminated its execution
        """
        logger.info("Starting main script. Simulation ID '%s'", self.sim_id)
        self.__exec_started_event.set()

        if self.__exec_thread is None or not self.__exec_thread.is_alive():
            self.__exec_thread = threading.Thread(target=self.__execute_script,
                                                  args=(completed_callback,),
                                                  daemon=True,
                                                  name="MainScriptThread")
            self.__exec_thread.start()

    def pause(self) -> None:
        logger.info("Pausing main script. Simulation ID '%s'", self.sim_id)
        self.__exec_started_event.clear()

    def stop(self) -> None:
        """
        Stops the script execution
        """
        logger.info("Stopping main script. Simulation ID '%s'", self.sim_id)
        if self.__exec_thread is not None:
            
            self.__exec_stopped_event.set()
            
            logger.debug("Waiting main script thread. Simulation ID '%s'", self.sim_id)
            
            self.__exec_thread.join(MAX_STOP_TIMEOUT) # NOTE Waiting point
            if self.__exec_thread.is_alive():
                logger.warning("Couldn't stop main script thread."
                               " Simulation ID '%s'", self.sim_id)

    def shutdown(self) -> None:
        logger.info("Shutdown main script. Simulation ID '%s'", self.sim_id)
        try:
            if self.__nrp_core_wrapped is None:
               logger.debug("Trying to shut NrpCore down twice. Ignoring. "
                            "Simulation ID '%s'", self.sim_id)
               return

            self.__nrp_core_wrapped._shutdown()
            self.__nrp_core_wrapped = None

        except Exception as e:
            logger.warning("NrpCore shutdown has thrown '%s'."
                           " Simulation ID '%s'", str(e), self.sim_id)
            raise

    @contextlib.contextmanager
    def _hide_modules(self, hide_list: List[str]):
        """
        Remove modules in hide_list from the sys.modules
        so to prevent accidental imports.

        It won't stop a motivated user though, for example, here is a workaround:

        import sys
        del sys.modules['module_name']
        import module_name
        """
        saved_modules = {module_name: sys.modules.get(module_name, None)
                         for module_name in hide_list}
        try:
            yield  # nothing to yield
        except Exception:
            raise # propagate exceptions
        finally:
            sys.modules.update(saved_modules)
