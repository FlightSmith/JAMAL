from typing import TYPE_CHECKING

import re
import logging
import functools
from typing import List, Optional, Union, Callable, LiteralString, Any
from app.utils.transformers import with_sanitized_value

logger = logging.getLogger(__name__)

# Regex patterns for numeric range validation
_float_pattern_str = (
    r"-?\d+(\.\d+)?([eE][-+]?\d+)?"  # Pattern for a single float, including scientific notation
)
_range_pattern_re = re.compile(rf"^{_float_pattern_str}:{_float_pattern_str}:{_float_pattern_str}$")
_single_float_pattern_re = re.compile(rf"^{_float_pattern_str}$")


def validate_with_itemized_value(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if isinstance(kwargs["sanitized_value"], list):
            sanitized_value = kwargs.pop("sanitized_value")
            logger.debug(f"sanitized_value - {sanitized_value}")
            return all(func(*args, sanitized_value=value, **kwargs) for value in sanitized_value)
        return func(*args, **kwargs)

    return wrapper


@with_sanitized_value
@validate_with_itemized_value
def validate_integer(
    column_name: str,
    data_object: dict,
    config: dict,
    validation_config,
    **kwargs,
) -> bool:
    """Validates if a value is an integer."""

    value = kwargs.get("sanitized_value")
    if not isinstance(value, str):
        return False
    try:
        int(value)
        return True
    except ValueError:
        return False


@with_sanitized_value
@validate_with_itemized_value
def validate_positive_integer(
    column_name: str,
    data_object: dict,
    config: dict,
    validation_config,
    **kwargs,
) -> bool:
    """Validates if a value is an positive integer."""
    value = kwargs.get("sanitized_value")
    if not isinstance(value, str):
        return False
    try:
        int_value = int(value)
        if int_value == abs(int_value):
            return True
        else:
            return False
    except ValueError:
        return False


@with_sanitized_value
@validate_with_itemized_value
def validate_float(
    column_name: str,
    data_object: dict,
    config: dict,
    validation_config,
    **kwargs,
) -> bool:
    """Validates if a value is a float."""
    value = kwargs.get("sanitized_value")
    logger.debug(f"value - {value} - type - {type(value)}")
    if not isinstance(value, str):
        logger.debug("not string")
        return False
    try:
        float(value)
        return True
    except ValueError:
        logger.debug("value error", exc_info=True)
        return False


@with_sanitized_value
@validate_with_itemized_value
def validate_string(
    column_name: str,
    data_object: dict,
    config: dict,
    validation_config,
    **kwargs,
) -> bool:
    """Validates if a value is a non-empty string."""
    value = kwargs.get("sanitized_value")
    if not isinstance(value, str):
        return False
    return bool(value)


from typing import Union


def _resolve_expected_length(
    column_name: str,
    validator_name: str,
    expected_length_raw: Union[int, str, None],
    validation_config,
) -> Union[int, None]:
    """Resolves the expected_length from config, handling REF resolution.

    Args:
        column_name: Name of the column being validated.
        validator_name: Name of the validator for logging purposes.
        expected_length_raw: Raw expected_length value from config (int, "REF", or None).
        validation_config: Global validation config for REF resolution.

    Returns:
        Resolved expected_length as int, or None if validation should fail.
    """
    if expected_length_raw is None:
        logger.warning(
            f"Validator '{validator_name}' requires 'expected_length' "
            f"in config for column '{column_name}'."
        )
        return None

    if expected_length_raw == "REF":
        if not validation_config:
            logger.error(
                f"Field '{column_name}' requires REF validation but "
                f"ValidationConfig was not provided"
            )
            return None

        expected_length = validation_config.get_expected_length(column_name)

        if expected_length is None:
            logger.error(
                f"Field '{column_name}' requires REF validation but section "
                f"not found in REF file"
            )
            return None

        logger.debug(f"Resolved expected_length from REF: {expected_length}")
        return expected_length

    return int(expected_length_raw)


def _validate_number_parts_with_trailing(
    column_name: str,
    parts: list[str],
) -> bool:
    """Validates number parts with trailing empty/missing value support.

    Rules:
    - All parts can be empty/missing ("-" or "") -> valid
    - Non-trailing parts must be valid numbers
    - Trailing parts (after last valid value) must be empty/missing

    Args:
        column_name: Name of the column being validated (for logging).
        parts: List of string parts to validate.

    Returns:
        True if all parts are valid according to trailing rules, False otherwise.
    """
    # Early return if all parts are empty/missing
    if all(p in ["-", ""] for p in parts):
        logger.debug(f"Field '{column_name}' has all empty/missing parts, skipping validation")
        return True

    # Find the last valid (non-empty/non-missing) part index
    last_valid = -1
    for i, part in enumerate(parts):
        if part not in ["-", ""]:
            last_valid = i

    # Validate non-trailing parts must be numeric
    for i in range(last_valid + 1):
        if parts[i] in ["-", ""]:
            logger.error(f"Field '{column_name}': empty/missing part not allowed at position {i}")
            return False
        try:
            float(parts[i])
        except ValueError:
            logger.error(f"Invalid numeric value in '{column_name}' at position {i}: {parts[i]}")
            return False

    # Validate trailing parts must be empty/missing
    for i in range(last_valid + 1, len(parts)):
        if parts[i] not in ["-", ""]:
            logger.error(
                f"Field '{column_name}': non-empty part not allowed at "
                f"trailing position {i}: {parts[i]}"
            )
            return False

    return True


def _validate_comma_separated_base(
    column_name: str,
    data_object: dict,
    config: dict,
    validation_config,
    kwargs: dict,
    validator_name: str,
    group_separator: str | None = None,
) -> bool:
    """Base validation logic for comma-separated values.

    Handles extraction, type checking, REF resolution, expected_length validation,
    and number validation with trailing support. Optionally flattens groups if a
    group_separator is provided.

    Args:
        column_name: Name of the column being validated.
        data_object: Dictionary with all data.
        config: Field-specific configuration dict with 'expected_length' key.
        validation_config: Global validation config for REF resolution.
        kwargs: Additional arguments including 'sanitized_value'.
        validator_name: Name of the validator for logging purposes.
        group_separator: Optional separator for splitting groups within comma-separated items.
                        If None, validates individual numbers. If provided (e.g., "/"),
                        splits each comma-separated item by this separator first.

    Returns:
        True if validation passes, False otherwise.
    """
    value = kwargs.get("sanitized_value")
    logger.debug(f"Validating {validator_name}: {value}")

    if not isinstance(value, str):
        return False

    # Split value into parts first
    parts = value.split(",")

    # If group_separator is provided, flatten the groups
    if group_separator is not None:
        parts = [element for item in parts for element in item.split(group_separator)]

    # Early return if all parts are empty/missing - skip length validation
    if all(p in ["-", ""] for p in parts):
        logger.debug(f"Field '{column_name}' has all empty/missing parts, skipping validation")
        return True

    # Get and resolve expected_length
    expected_length_raw = config.get("expected_length")
    logger.debug(f"expected_length (raw): {expected_length_raw}")

    expected_length = _resolve_expected_length(
        column_name, validator_name, expected_length_raw, validation_config
    )

    if expected_length is None:
        return False

    # Validate length (only after confirming not all parts are blank)
    original_parts = value.split(",")
    if len(original_parts) != expected_length:
        logger.error(
            f"Field '{column_name}': expected {expected_length} elements, "
            f"got {len(original_parts)}"
        )
        return False

    # Validate number parts with trailing support
    return _validate_number_parts_with_trailing(column_name, parts)


@with_sanitized_value
@validate_with_itemized_value
def validate_comma_separated_numbers(
    column_name: str,
    data_object: dict,
    config: dict,
    validation_config,
    **kwargs,
) -> bool:
    """Validates if a value is a comma-separated list of numbers or '-'.

    Example: "1.5,2.3,-,4.0"

    Rules:
    - All parts can be empty/missing ("-" or "") -> valid
    - Non-trailing parts must be valid numbers
    - Trailing parts (after last valid value) must be empty/missing
    - Supports REF resolution for expected_length

    Args:
        column_name: Name of the column being validated.
        data_object: Dictionary with all data.
        config: Field-specific configuration dict with 'expected_length' key.
        validation_config: Global validation config for REF resolution.
        **kwargs: Additional arguments including 'sanitized_value'.

    Returns:
        True if validation passes, False otherwise.
    """
    return _validate_comma_separated_base(
        column_name=column_name,
        data_object=data_object,
        config=config,
        validation_config=validation_config,
        kwargs=kwargs,
        validator_name="comma_separated_numbers",
    )


@with_sanitized_value
@validate_with_itemized_value
def validate_comma_separated_group_of_numbers(
    column_name: str,
    data_object: dict,
    config: dict,
    validation_config,
    **kwargs,
) -> bool:
    """Validates if a value is a comma-separated list of number groups or '-'.

    Groups are separated by '/' within each comma-separated item.
    Example: "1.5/2.0,3.3,-,4.0/5.1/6.2"

    Rules:
    - All parts can be empty/missing ("-" or "") -> valid
    - Non-trailing parts must be valid numbers
    - Trailing parts (after last valid value) must be empty/missing
    - Supports REF resolution for expected_length
    - Groups are flattened before validation

    Args:
        column_name: Name of the column being validated.
        data_object: Dictionary with all data.
        config: Field-specific configuration dict with 'expected_length' key.
        validation_config: Global validation config for REF resolution.
        **kwargs: Additional arguments including 'sanitized_value'.

    Returns:
        True if validation passes, False otherwise.
    """
    return _validate_comma_separated_base(
        column_name=column_name,
        data_object=data_object,
        config=config,
        validation_config=validation_config,
        kwargs=kwargs,
        validator_name="comma_separated_group_of_numbers",
        group_separator="/",
    )


@with_sanitized_value
@validate_with_itemized_value
def validate_numeric_range(
    column_name: str,
    data_object: dict,
    config: dict,
    validation_config,
    **kwargs,
) -> bool:
    """
    Validates if a value is a single float, a colon-separated range
    (float:float:float), or a comma-separated list of such ranges.
    """
    value = kwargs.get("sanitized_value", "")
    logger.debug(f"Validating numeric range for value: {value} - type {type(value)}")
    if isinstance(value, (int, float)):
        return True

    if not isinstance(value, str):
        return False

    value = value.strip()

    # Handle empty string case
    if not value:
        logger.debug(f"Value '{value}' is empty after stripping. Returning False.")
        return False

    # Check if it's a single float or a single range
    if _single_float_pattern_re.match(value) or _range_pattern_re.match(value):
        logger.debug(f"Value '{value}' matched single float or range pattern. Returning True.")
        return True

    # Check if it's a multi-range (contains commas)
    if "," in value:
        logger.debug(f"Value '{value}' contains commas. Checking as multi-range.")
        parts = [part.strip() for part in value.split(",")]
        if not all(parts):  # Handle cases like " , " or just ","
            logger.debug(
                f"Value '{value}' resulted in no valid parts after splitting and stripping. Returning False."
            )
            return False
        logger.debug(f"Split into parts: {parts}")
        for part in parts:
            # If any part is not a valid single float or range, the whole string is invalid
            if not (_range_pattern_re.match(part) or _single_float_pattern_re.match(part)):
                logger.debug(
                    f"Part '{part}' is not a valid single float or range. Returning False."
                )
                return False
        # If the loop completes, all parts are valid
        logger.debug(f"All parts in '{value}' are valid. Returning True.")
        return True

    # If none of the above formats match, it's invalid
    logger.debug(f"Value '{value}' did not match any valid numeric range format. Returning False.")
    return False


@with_sanitized_value
@validate_with_itemized_value
def validate_choice(
    column_name: str,
    data_object: dict,
    config: dict,
    validation_config,
    **kwargs,
) -> bool:
    """Validates if a value is in the list of allowed values."""
    logger.debug(f"column_name: {column_name}")
    logger.debug(f"data_object: {data_object}")
    logger.debug(f"config: {config}")
    logger.debug(f"kwargs: {kwargs}")

    value = kwargs.get("sanitized_value")

    # if not isinstance(value, str):
    #     return False

    if not value:
        return False

    allowed_values: Optional[list] = config.get("allowed_values")

    if isinstance(allowed_values, list):
        return value in allowed_values

    logger.warning(
        f"Validator 'choice' requires 'allowed_values' in config for column '{column_name}'."
    )
    return False  # Fail validation if allowed_values is missing
