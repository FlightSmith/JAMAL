import os
import logging
import json
import subprocess
from typing import Optional, Dict, Any, List

from utils.process_monitoring import monitor_process_output

# Get a logger instance for this module
logger = logging.getLogger(__name__)

# Constants for job execution modes
RUN_MODE_LOCAL = 0
RUN_MODE_QUEUE = 1
RUN_MODE_BATCH = 2

# Constants for run modes
RUN_MODE_SKIP = 0
RUN_MODE_EXECUTE = 1
RUN_MODE_FORCE = 2

# Default inactivity timeout (4 hours in seconds)
DEFAULT_INACTIVITY_TIMEOUT = 14400


class JamalExecutor:
    """
    A shell interface for executing CFD simulation cases using the Jamal solver.

    This class manages the execution of simulation cases by preparing the environment
    variables and executing bash scripts for CFD simulations. It handles the conversion
    of simulation case data into appropriate environment variables and manages the
    subprocess execution with proper logging and error handling.

    Attributes:
        filepath (str): Path to the input matrix file containing simulation parameters.
        run_counter (int): Counter tracking the number of executed simulation runs.
        job_mode (int): Job execution mode (0=local, 1=queue, 2=batch).
        version (str): Version identifier for the simulation.
        simulation_case: The simulation case object containing all parameters.
        verbose (bool): Flag to enable verbose output during execution.

    Raises:
        FileNotFoundError: If the specified input file does not exist.

    Example:
        >>> executor = JamalExecutor("/path/to/matrix.txt", jobmode=1, verbose=True)
        >>> executor.submit()
    """

    def __init__(self, filepath: str, **kwargs) -> None:
        """
        Initialize the JamalExecutor instance.

        Args:
            filepath (str): Path to the input matrix file.
            **kwargs: Additional configuration options:
                - jobmode (int): Job execution mode (default: 0)
                - version (str): Version identifier (default: "0")
                - simulation_case: Simulation case object (default: None)
                - verbose (bool): Enable verbose output (default: False)

        Raises:
            FileNotFoundError: If the input file does not exist.
        """
        self.filepath = filepath
        self.run_counter = 0
        self.job_mode = kwargs.get("jobmode", RUN_MODE_LOCAL)
        self.version = kwargs.get("version", "0")
        self.simulation_case = kwargs.get("simulation_case", None)
        self.verbose = kwargs.get("verbose", False)

        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Input file not found: {self.filepath}")

    def submit(self) -> None:
        """
        Submit the simulation case for execution.

        This method processes the simulation case and submits it for execution
        if the run flag is set appropriately.
        """
        self._process_run_flags()

    def _process_run_flags(self) -> bool:
        """
        Process simulation case with RUN flag set to execute.

        Returns:
            bool: True if the case was processed successfully, False otherwise.
        """
        if not self.simulation_case:
            logger.warning("No simulation case provided.")
            return False

        line_num = self.simulation_case.line_number

        # Check if the simulation case should run (run_mode 1 or 2)
        run_mode = self.simulation_case.get_run_mode
        if run_mode not in (RUN_MODE_EXECUTE, RUN_MODE_FORCE):
            logger.debug(f"Skipping case at line {line_num} - run_mode is {run_mode}")
            return False

        if not self._send_to_bash():
            logger.error(f"Failed to send simulation case for line {line_num} to bash.")
            return False

        self.run_counter += 1
        return True

    def _send_to_bash(self) -> bool:
        """
        Send a processed simulation case to a bash script for execution.

        Returns:
            bool: True if the bash command was executed successfully, False otherwise.
        """
        env = self._prepare_bash_environment()

        if self.verbose and self.simulation_case:
            logger.debug(f"Running case: {self.simulation_case.POL}")

        command = ["/bin/bash","jamal.sh"]
        logger.info(f"Executing bash command: {command}")

        try:
            # Use subprocess.Popen for better control and error handling
#            process = subprocess.Popen(
#                command,
#                env=env,
#                stdout=subprocess.PIPE,
#                stderr=subprocess.STDOUT,
#                text=True,  # Decode stdout and stderr as text
#            )

#            if process.stdout is None:
#                raise RuntimeError("Process stdout is None - subprocess configuration error")
#            process.communicate(timeout=14400)

#            monitor_process_output(
#                process,
#                logging_verbosity=1,
#                inactivity_timeout=DEFAULT_INACTIVITY_TIMEOUT,
#                log_level=logging.INFO,
#            )
#
            rc = monitor_process_output(
                command,
                env=env,
                logging_verbosity=1,
                inactivity_timeout=DEFAULT_INACTIVITY_TIMEOUT,
                log_level=logging.INFO,
            )

#            rc = process.returncode

            if rc  != 0:
                logger.error(f"Bash command failed with return code {rc}")
                return False

            if self.verbose and self.simulation_case:
                logger.debug(f"Finished: {self.simulation_case.POL}")

            logger.info("Bash command executed successfully.")
            return True

        except FileNotFoundError:
            logger.error(
                f"Command not found: {command}",
                exc_info=True,
            )
            return False

        except RuntimeError:
            # Re-raise RuntimeError after logging
            raise

        except Exception as e:
            logger.error(
                f"An unexpected error occurred during bash execution: {e}",
                exc_info=True,
            )
            return False

    def _prepare_bash_environment(self) -> Dict[str, str]:
        """
        Prepare the environment variables for the bash script execution.

        Returns:
            Dict[str, str]: A dictionary representing the environment variables.
        """
        env = os.environ.copy()  # Create a copy to avoid modifying the global os.environ

        # Set basic environment variables
        env["matrix"] = self.filepath
        env["version"] = str(self.version)

        if self.job_mode != RUN_MODE_LOCAL:
            env["jamal_mode"] = str(self.job_mode)

        # Get simulation case data if available
        if self.simulation_case:
            simulation_case_dict = self.simulation_case.to_dict()
            logger.debug(f"simulation_case_dict - {simulation_case_dict}")
            simulation_case_dict["mach_sweep"] = self.simulation_case.is_mach_sweep
            #simulation_case_dict["cnfg"] = simulation_case_dict["AERODYNAMIC_CONFIGURATION"][0]
            simulation_case_dict["define_probes"] = self.simulation_case.define_probes

            # Flatten slash-separated fields
            for field in ["FANINLET", "FANOULET", "COREEXHA", "PROPELLER"]:
                if field in simulation_case_dict:
                    simulation_case_dict[field] = self._flatten_slash_separated(
                        simulation_case_dict[field]
                    )

            # Process each variable based on its type
            for var_name, data in simulation_case_dict.items():
                # Sanitize variable name for bash
                var_name = str(var_name)
                sanitized_var_name = var_name.replace("]", "").replace("[", "_")

                if isinstance(data, list):
                    # For lists, convert all elements to strings and format for Bash array
                    str_elements = [str(elem) for elem in data]
                    sanitized_list_var_name = sanitized_var_name + "_ARRAY"
                    env[sanitized_list_var_name] = json.dumps(str_elements)
                    logger.debug(
                        f"Setting environment variable {sanitized_list_var_name}={env[sanitized_list_var_name]}"
                    )
                else:
                    # For simple variables, just convert to string
                    # Apply specific formatting for POL if needed
                    env[sanitized_var_name] = (
                        str(data).zfill(3) if sanitized_var_name == "POL" else str(data)
                    )
                    logger.debug(
                        f"Setting environment variable {sanitized_var_name}={env[sanitized_var_name]}"
                    )

        return env

    def _flatten_slash_separated(self, data: List[str]) -> List[str]:
        """
        Flatten a list of slash-separated strings into a single list.

        Args:
            data: List of strings where each string may contain slash-separated values.

        Returns:
            List[str]: Flattened list of individual elements.
        """
        return [element for item in data for element in item.split("/")]


# Backward compatibility alias
JamalShell = JamalExecutor
