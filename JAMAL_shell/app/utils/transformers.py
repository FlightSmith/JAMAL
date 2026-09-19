import re
import logging
import functools
from typing import List, Optional, Union, Callable

logger = logging.getLogger(__name__)

# Regex patterns for bracketed columns
_has_brackets_re = re.compile(r"^\[(.*)\]$")
_has_brackets_mismatch_re = re.compile(r"^[^\[\]]*(\[|\])[^\[\]]*$")
_has_brackets_in_wrong_place_re = re.compile(r"^(?!\[.*\]$).*[\[\]].*$")
_header_bracket_re = re.compile(
    r"^([A-Za-z0-9_]+)\_([A-Za-z0-9_]+)$"
)  # Regex to parse NAME[VALUE] headers


def with_sanitized_value(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        data_object = kwargs.get("data_object")
        config = kwargs.get("config")
        column_name = kwargs.get("column_name")
        logger.debug(f"column_name: {column_name}")
        logger.debug(f"data_object: {data_object}")
        logger.debug(f"config: {config}")
        sanitized_value = sanitize_bracketed_value(
            column_name=column_name, data_object=data_object, config=config
        )
        logger.debug(f"sanitized_value - {sanitized_value}")
        kwargs["sanitized_value"] = sanitized_value
        return func(*args, **kwargs)

    return wrapper


def sanitize_bracketed_value(
    column_name: str, data_object: dict, config: dict
) -> Optional[str]:
    """
    Handles validation and extraction of values based on bracket configuration.

    Args:
        column_name: The name of the column being processed.
        value: The raw value of the field.
        config: Dictionary with column configuration.

    Returns:
        The value to validate (with brackets removed if configured and present)
        or None if there is a bracket-related validation error.
    """
    value = data_object.get(column_name)
    logger.debug(f"value - {value}")
    if not value:
        return value

    if isinstance(value, list):
        logger.debug(f"value is list - {value}")
        return value

    bracketed_config = config.get("bracketed", False)
    has_brackets_match = _has_brackets_re.match(value)

    # Case 1: Column doesn't expect brackets but they are present
    if not bracketed_config and has_brackets_match:
        logger.critical(
            f"Column '{column_name}' did not expect brackets but found them."
        )
        return None

    # Case 2: Column expects brackets and they are correctly placed
    if bracketed_config and has_brackets_match:
        return has_brackets_match.group(1)

    # Case 3: Check for bracket mismatch (only one bracket)
    if _has_brackets_mismatch_re.match(value):
        logger.critical(
            f"Column '{column_name}' has brackets mismatch (unpaired bracket)."
        )
        return None

    # Case 4: Check for brackets in wrong places
    if "[" in value or "]" in value:
        # This means there are brackets, but they're not properly enclosing the value
        logger.critical(f"Column '{column_name}' has brackets in the wrong place.")
        return None

    return value


def transform_bracketed_column(
    column_name: str, data_object: dict, config: dict
) -> None:
    """
    Processes a column marked as 'bracketed' in the configuration.

    Derives a new column name and value based on the header format (NAME[VALUE])
    and whether the data field itself contains brackets. Modifies the
    data_object in place.

    Args:
        column_name: The original column name from the header (e.g., "MACH[VEL]").
        data_object: The dictionary being built for the current line.
    """

    value = data_object.get(column_name)
    if isinstance(value, list):
        logger.debug("Value is list. already separated")
        return True

    header_match = _header_bracket_re.match(column_name)
    if header_match:
        outside_part = header_match.group(1)
        inside_part = header_match.group(2)
        # Create a derived column name like 'mach_vel_mode'
        new_column_name = f"{outside_part.lower()}_{inside_part.lower()}_mode"
        value_has_brackets = _has_brackets_re.match(value)

        if value_has_brackets:
            # If the value has brackets (e.g., "[some_value]"), use the part inside the header brackets
            data_object[new_column_name] = inside_part
            logger.debug(
                f"Added derived column '{new_column_name}' "
                f"with value '{inside_part}' (value had brackets)."
            )
            data_object[column_name] = value_has_brackets.groups()[0]
        else:
            # If the value does not have brackets, use the part outside the header brackets
            data_object[new_column_name] = outside_part
            logger.debug(
                f"Added derived column '{new_column_name}' "
                f"with value '{outside_part}' (value had no brackets)."
            )
    else:
        # Log a warning if the configuration expects brackets but the header doesn't match
        logger.warning(
            f"Column '{column_name}' is marked 'bracketed' "
            f"but doesn't match NAME[VALUE] format."
        )
    return True


def _frange(start: float, stop: float, step: float) -> List[float]:
    """Generate a range of floating point numbers.

    Args:
        start: Starting value
        stop: Stopping value
        step: Step size

    Returns:
        List of float values in the range, inclusive of both start and stop
        when they align with the step size.
    """
    # Special case: step=0
    if step == 0:
        if start == stop:
            # Valid case: return only the initial value
            return [round(start, 10)]
        else:
            # Invalid case: step=0 but start≠stop
            raise ValueError(f"Step cannot be zero for a range where start != end.")

    result = []
    # Calculate number of steps to avoid precision issues
    num_steps = int(round((stop - start) / step)) + 1

    # Generate values using index to avoid error accumulation
    for i in range(num_steps):
        # Calculate current value using multiplication instead of repeated addition
        value = start + i * step
        # Round to avoid precision issues
        rounded_value = round(value, 10)

        result.append(rounded_value)

    return result


def _parse_single_set(set_str: str) -> list:
    """
    Parses a single set string, which can be a number or a range.

    Args:
        set_str (str): The string representation of the set (e.g., "10", "1:2:10").

    Returns:
        list: A list of expanded numerical values from the set.

    Raises:
        ValueError: If the set_str format is invalid or parsing fails.
    """
    logger.debug(f"Parsing set string: '{set_str}'")
    expanded_values = []

    if ":" in set_str:
        parts = set_str.split(":")
        if len(parts) != 3:
            raise ValueError(
                f"Invalid range format: '{set_str}'. Expected 'start:step:end'."
            )

        start, step, end = float(parts[0]), float(parts[1]), float(parts[2])
        logger.debug(f"Parsed range components: start={start}, step={step}, end={end}")

        if step == 0 and start != end:
            raise ValueError(
                f"Invalid range format: '{set_str}'. Step cannot be zero for a range where start != end."
            )

        # Adjust step direction if start > end
        if start > end and step > 0:
            step = -step
            logger.debug(f"Adjusted step to negative: {step} as start > end")
        elif start < end and step < 0:
            raise ValueError(f"Step is negative and start < end: '{set_str}'. .")

        if start == end:
            expanded_values.append(start)
            logger.debug(f"Range start equals end, added single value: {start}")
        else:
            # Assuming _frange handles step direction correctly
            range_values = list(_frange(start, end, step))
            expanded_values.extend(range_values)
            logger.debug(f"Expanded range '{set_str}' to {range_values}.")
            logger.debug(f"Expanded range now: {expanded_values}")

    else:
        try:
            value = float(set_str)
            logger.debug(f"Parsed single value: {value}")
            expanded_values.append(value)
            logger.debug(f"Added float value: {value}")
        except ValueError as e:
            raise ValueError(
                f"Invalid value format: '{set_str}' - could not convert to number."
            ) from e

    logger.debug(f"Returning expanded range now: {expanded_values}")
    return expanded_values


def transform_expand_range(
    column_name: str, data_object: dict, config: dict, value=""
) -> bool:
    """Expand a range string into a list of numeric values.

    Args:
        value: The value containing ranges
        data_object: The dictionary being built for the current line.

    Returns:
        List of expanded values
    """
    value = data_object.get(column_name)

    if not isinstance(value, list):
        value_list = [value]
    else:
        value_list = value.copy()

    logger.debug(f"Expanding range for each value in '{value_list}'")

    expanded_values = []

    for value in value_list:
        if isinstance(value, (int, float)):
            expanded_set = [value]
            logger.debug(f"{value} is {type(value)}. not expanding")
        else:

            sets = value.split(",")

            expanded_set = []
            for set_str in sets:
                try:
                    expanded_set.extend(_parse_single_set(set_str))
                    logger.debug(f"Expanded values: {expanded_set}")
                except ValueError as e:
                    # Log handled by _parse_single_set, just re-raise or handle differently
                    # Depending on desired error propagation
                    logger.error(f"Failed to process set '{set_str}': {e}")
                    raise  # Re-raise the specific ValueError from the helper
        expanded_values.extend(expanded_set)
        logger.debug(
            f"Updating values on data_object key: {column_name} | value: {expanded_values}"
        )
    data_object[column_name] = sorted(expanded_values)
    return True


def transform_split_configured_fields(
    column_name: str, data_object: dict, config: dict
) -> bool:
    """
    Splits string field values in the data_object into lists based on
    separators defined in COLUMN_CONFIG. Modifies the data_object in place.

    Args:
        column_name: The original column name from the header (e.g., "MACH[VEL]").
        data_object: The dictionary being built for the current line.

    Returns:
        True if splitting was successful or not required, False otherwise.
    """
    value = data_object[column_name]
    separators = config.get("separator")
    if isinstance(value, list):
        logger.debug("Value is list. already separated")
        return True
    if not isinstance(value, str):
        logger.debug("List value not compatible with separator")
        return False
    # Escape potential regex special characters in the separator string
    # Split using any character in the separator string
    # Filter out empty strings resulting from adjacent separators or start/end separators
    split_values = [
        part for part in re.split(f"[{re.escape(separators)}]", value) if part
    ]

    # Update the data_object with the list of strings
    data_object[column_name] = split_values
    logger.debug(
        "Split column '%s' value '%s' into %s using separator '%s'",
        column_name,
        value,
        data_object[column_name],
        separators,
    )
    return True


def transform_mach_sweep(column_name: str, data_object: dict, config: dict) -> bool:
    mach_vel = data_object[column_name]
    data_object["mach_sweep"] = bool(mach_vel) and not all(
        item == mach_vel[0] for item in mach_vel
    )
    return True


def transform_alpha_cl_sweep(column_name: str, data_object: dict, config: dict) -> bool:
    alpha_cl = data_object[column_name]
    data_object["alpha_cl_sweep"] = bool(alpha_cl) and not all(
        item == alpha_cl[0] for item in alpha_cl
    )
    return True


def transform_beta_cy_sweep(column_name: str, data_object: dict, config: dict) -> bool:
    beta_cy = data_object[column_name]
    data_object["beta_cy_sweep"] = bool(beta_cy) and not all(
        item == beta_cy[0] for item in beta_cy
    )
    return True
