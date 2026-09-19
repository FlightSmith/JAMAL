#!/usr/bin/env python
import argparse
import logging
import sys
import os
import json
import yaml


# from app.core.simcase import SimulationCase

# Define the script version
__version__ = os.environ.get("JAMAL_VERSION", "DEV")

JAMAL_BIN = os.path.dirname(__file__)
JAMAL_ROOT = os.path.abspath(os.environ.get("JAMAL_ROOT", os.path.dirname(JAMAL_BIN)))

sys.path.append(JAMAL_ROOT)

# Import the logging setup function and the placeholder parser
try:
    from utils.logger import setup_logging
    from utils.misc import show_banner
    from app.core.workaround_to_shell import JamalShell
    from app.core.simulation_case import get_cases_from_matrix, SimulationCase
    from app.core.mesh_processor import MeshProcessor
except ImportError as e:
    # Basic logging if imports fail before setup_logging is available
    print(f"Error importing necessary modules: {e}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    logger = setup_logging()
    """
    Main function to parse arguments, configure logging, and process the input file.
    """
    show_banner(version=__version__)

    parser = argparse.ArgumentParser(description="Process an input matrix file.")

    # Required positional argument for the input file path
    parser.add_argument("filepath", help="Path to the input matrix file.")

    # Optional arguments for version and help (help is automatic)
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show the script's version and exit.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Increase verbosity (JAMAL SHELL).",
    )
    # Optional arguments for logging verbosity control
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Set log level to ERROR (suppress warnings and info).",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="count",
        default=0,
        help="Increase log verbosity (-d for INFO, -dd or more for DEBUG).",
    )
    parser.add_argument(
        "-j",
        "--job-mode",
        dest="job_mode",
        type=int,
        choices=[0, 1, 2],  # Restricts input to valid modes, preventing invalid values
        default=0,
        help=(
            "Specify the job mode: 0 (default) prepares files including 'to_run.sh'; "
            "1 submits the job case; 2 submits the job and monitors output to execute 'postproc'."
        ),
    )

    # Parse the command line arguments
    args = parser.parse_args()

    # Validate mutual exclusivity of -q and -d
    if args.quiet and args.debug > 0:
        parser.error("Arguments -q/--quiet and -d/--debug are mutually exclusive.")

    # Determine the effective log level based on arguments
    log_level = logging.WARNING  # Default level
    if args.quiet:
        log_level = logging.ERROR
    elif args.debug == 1:
        log_level = logging.INFO
    elif args.debug >= 2:
        log_level = logging.DEBUG

    # Configure logging
    logger = setup_logging(logger=logger, log_level=log_level)

    # Log script start and effective log level
    logger.info("Script started. Log level set to %s", logging.getLevelName(log_level))

    # Log the file being processed
    logger.debug("Processing file: %s", args.filepath)

    # Core Logic Execution (with Error Handling)
    try:
        # Instantiate and call the main processing logic
        data_objects = get_cases_from_matrix(filepath=args.filepath)

        if not data_objects:
            logger.warning("No polar set to run.")

        for data_object in data_objects:
            try:
                # if True:
                simulation_case_instance = SimulationCase.from_dict(data_object)
                logger.info(f"simulation_case_instance - {simulation_case_instance}")

                simulation_case_instance = MeshProcessor.process(simulation_case_instance)
                js = JamalShell(
                    filepath=args.filepath,
                    jobmode=args.job_mode,
                    version=__version__,
                    simulation_case=simulation_case_instance,
                    verbose=args.verbose,
                )
                js.submit()
            except Exception as e:
                logger.error(f"Failed to process simulation case: {e}", exc_info=True)

        # Log successful completion
        logger.info("Processing completed successfully.")

    except FileNotFoundError:
        # FileNotFoundError is handled by MatrixParser, just log and exit
        # The MatrixParser constructor already logs the specific file not found error
        sys.exit(1)
    except Exception:
        # Catch any other unexpected exceptions and log with traceback
        logger.exception("An unexpected error occurred during processing.")
        sys.exit(1)


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    main()
