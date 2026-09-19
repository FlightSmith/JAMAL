import os
import yaml
import logging


# Get a logger instance for this module
logger = logging.getLogger(__name__)

COLORS = {
    "RESET": "\033[0m",
    "WHITE": "\033[38;5;255m",
    "LIGHT_GRAY": "\033[38;5;253m",
    "YELLOW": "\033[38;5;226m",
    "ORANGE": "\033[38;5;220m",
    "DEEP_ORANGE": "\033[38;5;202m",
    "BROWN_ORANGE": "\033[38;5;130m",
    "DARK_ORANGE": "\033[38;5;94m",
    "LIGHT_GREEN": "\033[38;5;106m",
    "GREEN": "\033[38;5;70m",
    "DARK_GREEN": "\033[38;5;34m",
    "GREEN_CYAN": "\033[38;5;35m",
    "CYAN": "\033[38;5;36m",
    "LIGHT_BLUE": "\033[38;5;37m",
    "BLUE": "\033[38;5;38m",
    "DARK_BLUE": "\033[38;5;39m",
    "YELLOW_BLINK": "\033[38;5;226;5m",
}


def show_banner(version: str = "DEVELOPMENT") -> None:
    """
    Displays the JAMAL banner in the terminal using ANSI colors, with 'PYTHON' instead of 'script'.
    The version string is displayed below the banner.

    Args:
        version (str): The version to display. Defaults to "DEVELOPMENT".
    """
    # Configure logging to output to the console with no extra formatting
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Define the banner lines with ANSI color codes
    banner_lines = [
        f"{COLORS['WHITE']       }                                                                                           {COLORS['RESET']}",
        f"{COLORS['LIGHT_GRAY']  } ██╗   ██╗ █████╗ ██╗     ██╗      █████╗          ██╗ █████╗ ███╗   ███╗ █████╗ ██╗       {COLORS['RESET']}",
        f"{COLORS['YELLOW']      } ╚██╗ ██╔╝██╔══██╗██║     ██║     ██╔══██╗         ██║██╔══██╗████╗ ████║██╔══██╗██║       {COLORS['RESET']}",
        f"{COLORS['ORANGE']      }  ╚████╔╝ ███████║██║     ██║     ███████║         ██║███████║██╔████╔██║███████║██║       {COLORS['RESET']}",
        f"{COLORS['DEEP_ORANGE'] }   ╚██╔╝  ██╔══██║██║     ██║     ██╔══██║    ██   ██║██╔══██║██║╚██╔╝██║██╔══██║██║       {COLORS['RESET']}",
        f"{COLORS['BROWN_ORANGE']}    ██║   ██║  ██║███████╗███████╗██║  ██║    ╚█████╔╝██║  ██║██║ ╚═╝ ██║██║  ██║███████╗  {COLORS['RESET']}",
        f"{COLORS['BROWN_ORANGE']}    ╚═╝   ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝     ╚════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝  {COLORS['RESET']}",
        f"{COLORS['DARK_ORANGE'] }                                                                                           {COLORS['RESET']}",
        f"{COLORS['DARK_ORANGE'] }                                             o8o                 .                         {COLORS['RESET']}",
        f"{COLORS['LIGHT_GREEN'] }                                             \"\"                .o8                       {COLORS['RESET']}",
        f"{COLORS['GREEN']       }                 .oooo.o  .ooooo.  oooo d8b oooo  oo.ooooo.  .o888oo                       {COLORS['RESET']}",
        f"{COLORS['DARK_GREEN']  }                d88\"  \"8 d88\"  \"Y8  888\"\"8P  888   888\"  888b   888                 {COLORS['RESET']}",
        f"{COLORS['GREEN_CYAN']  }                 \"Y88b.  888        888      888   888   888                              {COLORS['RESET']}",
        f"{COLORS['CYAN']        }                o.  .88b 888   .o8  888      888   888   888   888 .                       {COLORS['RESET']}",
        f"{COLORS['LIGHT_BLUE']  }                8\"\"888P\"  Y8bod8P\" d888b    o888o  888bod8P\"   \"888\"                {COLORS['RESET']}",
        f"{COLORS['BLUE']        }                                                   888                                     {COLORS['RESET']}",
        f"{COLORS['DARK_BLUE']   }                                                   o888o                                   {COLORS['RESET']}",
        "                                                                                                                ",
        "            Job Automation and Management of Aerodynamic simuLations (CFD)                                      ",
        f"                                  version {version}                                     ",
        "                                                                                                                ",
        f"                                   {COLORS['YELLOW_BLINK']}INSERT COIN{COLORS['RESET']}                                           ",
    ]

    # New ASCII for "PYTHON" (custom, simple, and color-matched)
    python_ascii = [
        f"{COLORS['DARK_ORANGE'] }                                                                                           {COLORS['RESET']}",
        f"{COLORS['LIGHT_GREEN'] }                  ██████╗ ██╗   ██╗████████╗██╗  ██╗ ██████╗ ███╗   ██╗                    {COLORS['RESET']}",
        f"{COLORS['GREEN']       }                  ██╔══██╗╚██╗ ██╔╝╚══██╔══╝██║  ██║██╔═══██╗████╗  ██║                    {COLORS['RESET']}",
        f"{COLORS['DARK_GREEN']  }                  ██████╔╝ ╚████╔╝    ██║   ███████║██║   ██║██╔██╗ ██║                    {COLORS['RESET']}",
        f"{COLORS['GREEN_CYAN']  }                  ██╔═══╝   ╚██╔╝     ██║   ██╔══██║██║   ██║██║╚██╗██║                    {COLORS['RESET']}",
        f"{COLORS['CYAN']        }                  ██║        ██║      ██║   ██║  ██║╚██████╔╝██║ ╚████║                    {COLORS['RESET']}",
        f"{COLORS['LIGHT_BLUE']  }                  ╚═╝        ╚═╝      ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝                    {COLORS['RESET']}",
        f"{COLORS['BLUE']        }                                                                                           {COLORS['RESET']}",
        f"{COLORS['DARK_BLUE']   }                                                                                           {COLORS['RESET']}",
    ]
    # Substitute the lines in the banner
    banner_lines[8:17] = python_ascii

    # Output each line using logging
    for line in banner_lines:
        print(line)


def load_config():
    """
    Loads column configuration from the YAML file.

    Returns:
        dict: Column configuration loaded from the YAML file.

    Raises:
        FileNotFoundError: If the configuration file is not found.
        EnvironmentError: If the JAMAL_ROOT environment variable is not defined.
        yaml.YAMLError: If there is an error parsing the YAML file.
    """
    try:
        # Get the root directory from the environment variable
        jamal_root = os.environ.get("JAMAL_ROOT")
        if not jamal_root:
            error_msg = "JAMAL_ROOT environment variable not defined"
            logger.error(error_msg)
            raise EnvironmentError(error_msg)

        # Build the full path to the YAML file
        config_path = os.path.join(jamal_root, "etc", "jamal.yml")

        # Check if the file exists
        if not os.path.isfile(config_path):
            error_msg = f"Configuration file not found: {config_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        # Open and load the YAML file
        logger.info(f"Loading column configuration from {config_path}")
        with open(config_path, "r") as yaml_file:
            column_config = yaml.safe_load(yaml_file)

        logger.info(
            f"Configuration successfully loaded: {len(column_config)} columns set defined"
        )
        return column_config

    except yaml.YAMLError as e:
        error_msg = f"Error parsing YAML file: {e}"
        logger.error(error_msg)
        raise
    except Exception as e:
        error_msg = f"Unexpected error loading configuration: {e}"
        logger.error(error_msg)
        raise
