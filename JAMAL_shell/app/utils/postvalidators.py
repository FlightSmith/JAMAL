import logging

logger = logging.getLogger(__name__)


def post_validator_alpha_beta_sweep(
    column_name: str,
    data_object: dict,
    config: dict,
    validation_config,
) -> bool:
    """
    Custom processor for the 'alpha_beta_sweep'.

    Args:
        value: The validated value of the field.
        data_object: The dictionary representing the current line's data,
                     which can be modified by this function.
    """
    if len(data_object["ALPHA_CLS"]) > 1 and len(data_object["BETA_CYS"]) > 1:
        logger.error("Alpha sweep and Beta Sweep not allowed")
        return False
    # Placeholder implementation - add actual processing logic here if needed
    return True


def post_validator_alpha_mach_sweep(
    column_name: str,
    data_object: dict,
    config: dict,
    validation_config,
) -> bool:
    """
    Custom processor for the 'alpha_mach_sweep'.

    Args:
        value: The validated value of the field.
        data_object: The dictionary representing the current line's data,
                     which can be modified by this function.
    """
    if len(data_object["ALPHA_CLS"]) > 1 and len(data_object["MACH_VEL"]) > 1:
        logger.error("Alpha sweep and MACH Sweep not allowed")
        return False
    # Placeholder implementation - add actual processing logic here if needed
    return True


def post_validator_beta_mach_sweep(
    column_name: str,
    data_object: dict,
    config: dict,
    validation_config,
) -> bool:
    """
    Custom processor for the 'beta_mach_sweep'.

    Args:
        value: The validated value of the field.
        data_object: The dictionary representing the current line's data,
                     which can be modified by this function.
    """
    if len(data_object["BETA_CYS"]) > 1 and len(data_object["MACH_VEL"]) > 1:
        logger.error("Beta sweep and MACH Sweep not allowed")
        return False
    # Placeholder implementation - add actual processing logic here if needed
    return True


def post_validator_mach_vel(
    column_name: str,
    data_object: dict,
    config: dict,
    validation_config,
) -> bool:
    """
    Custom processor for the 'mach_vel'.

    Args:
        value: The validated value of the field.
        data_object: The dictionary representing the current line's data,
                     which can be modified by this function.
    """
    if data_object["mach_vel_mode"] == "VEL" and data_object["rey_alt_mode"] == "REY":
        logger.error("Defining Velocity and Reynolds is not permited")
        return False
    # Placeholder implementation - add actual processing logic here if needed
    return True


def post_validator_positive_values(
    column_name: str,
    data_object: dict,
    config: dict,
    validation_config,
) -> bool:
    """
    Validates if the value in data_object[column_name] is positive.

    Args:
        column_name: The key to access the value in data_object
        data_object: Dictionary containing the data to validate

    Returns:
        bool: True if all values are positive, False otherwise

    Raises:
        KeyError: If column_name doesn't exist in data_object
        ValueError: If values cannot be converted to numeric
    """

    # Check if column exists in data_object
    if column_name not in data_object:
        logger.error(f"Column '{column_name}' not found in data_object")
        raise KeyError(f"Column '{column_name}' not found in data_object")

    value = data_object[column_name]

    # Handle different data types
    if isinstance(value, list):
        # If value is a list, check each element
        if not value:  # Empty list
            logger.warning(f"Empty list found in '{column_name}'")
            return False

        for item in value:
            if not _is_positive(item):
                logger.info(f"Non-positive value found in list: {item}")
                return False
        return True
    else:
        # Single value
        return _is_positive(value)


def _is_positive(value) -> bool:
    """
    Helper function to check if a value is positive.

    Args:
        value: The value to check

    Returns:
        bool: True if value is positive, False otherwise
    """

    try:
        # Handle different types
        if isinstance(value, (int, float)):
            numeric_value = value
        elif isinstance(value, str):
            # Try to convert string to float
            numeric_value = float(value)
        else:
            logger.warning(f"Unsupported type: {type(value)}")
            return False

        # Check if positive
        return numeric_value >= 0
    except ValueError:
        logger.error(f"Cannot convert value to numeric: {value}")
        return False
