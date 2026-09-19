from __future__ import annotations
from pydantic import BaseModel, ConfigDict, ValidationError
from typing import Dict, Any, List, Optional, Callable, Set, Union, Protocol, runtime_checkable
import logging
import yaml
import os
import re
from utils.misc import load_config
from app.utils import validators, transformers, postvalidators
from app.utils.ref_metadata import RefMetadata
from app.utils.ref_parser import parse_ref_file, resolve_ref_filepath

logger = logging.getLogger(__name__)


# =============================================================================
# Protocol Classes for Type Safety
# =============================================================================


@runtime_checkable
class ValidatorFunc(Protocol):
    """Protocol for validator functions."""

    def __call__(
        self,
        column_name: str,
        data_object: Dict[str, Any],
        config: Dict[str, Any],
        validation_config: "ValidationConfig",
        **kwargs: Any,
    ) -> bool: ...


@runtime_checkable
class TransformerFunc(Protocol):
    """Protocol for transformer functions."""

    def __call__(
        self,
        column_name: str,
        data_object: Dict[str, Any],
        config: Dict[str, Any],
    ) -> bool: ...


@runtime_checkable
class PostValidatorFunc(Protocol):
    """Protocol for post-validator functions."""

    def __call__(
        self,
        column_name: str,
        data_object: Dict[str, Any],
        config: Dict[str, Any],
        validation_config: "ValidationConfig",
    ) -> bool: ...


# =============================================================================
# Pipeline Step Registry
# =============================================================================

PIPELINE_REGISTRY: Dict[str, Dict[str, Callable]] = {
    "validator": {
        "positive_integer": validators.validate_positive_integer,
        "integer": validators.validate_integer,
        "string": validators.validate_string,
        "comma_separated_numbers": validators.validate_comma_separated_numbers,
        "comma_separated_group_of_numbers": validators.validate_comma_separated_group_of_numbers,
        "numeric_range": validators.validate_numeric_range,
        "choice": validators.validate_choice,
        "float": validators.validate_float,
    },
    "transformer": {
        "split_configured_fields": transformers.transform_split_configured_fields,
        "bracketed_column": transformers.transform_bracketed_column,
        "expand_range": transformers.transform_expand_range,
    },
    "post-validator": {
        "alpha_beta_sweep": postvalidators.post_validator_alpha_beta_sweep,
        "alpha_mach_sweep": postvalidators.post_validator_alpha_mach_sweep,
        "beta_mach_sweep": postvalidators.post_validator_beta_mach_sweep,
        "mach_vel": postvalidators.post_validator_mach_vel,
        "positive_values": postvalidators.post_validator_positive_values,
    },
}


def get_cases_from_matrix(filepath: str) -> List[Dict[str, Any]]:
    """
    Parse matrix file and extract simulation cases.

    Args:
        filepath: Path to the matrix file

    Returns:
        List of dictionaries representing simulation cases

    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If header is invalid
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Input file not found: {filepath}")

    header = None
    results = []

    with open(filepath, "r") as matrix_file:
        lines = matrix_file.readlines()

    header_line = lines[0].strip()
    if not header_line or header_line.startswith("#"):
        error_msg = f"Invalid header: {'Empty header' if not header_line else 'Header starts with comment character #'}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    header = re.split(r"\s+", header_line)

    for line_num, line in enumerate(lines[1:], 2):
        line = line.strip()

        if not line or line.startswith(("#", "0")):
            continue

        values = re.split(r"\s+", line)

        if len(values) != len(header):
            logger.warning(f"Mismatch values ({len(values)}) and headers ({len(header)})")
            continue

        data = dict(zip(header, values))
        data["line_number"] = line_num
        results.append(data)

    return results


class CaseValidationError(Exception):
    """Custom exception for case validation errors."""

    pass


class ValidationConfig:
    """Encapsulates validation configuration logic."""

    def __init__(self, column_config: Dict[str, Any], ref_metadata: Optional[RefMetadata] = None):
        self.column_config = column_config
        self.ref_metadata = ref_metadata

    def get_field_config(self, field_name: str) -> Dict[str, Any]:
        """Get configuration for a specific field."""
        return self.column_config.get(field_name, {})

    def get_expected_length(self, field_name: str) -> Optional[int]:
        """
        Get expected length for a field, resolving REF if needed.

        Args:
            field_name: Name of the field

        Returns:
            Expected length as integer, or None if not defined

        Raises:
            ValueError: If REF is required but metadata is not available
        """
        field_config = self.get_field_config(field_name)
        expected_length = field_config.get("expected_length")

        # If not REF-based, return as-is
        if expected_length != "REF":
            return expected_length

        # REF-based validation
        if not self.ref_metadata:
            raise ValueError(f"Field '{field_name}' requires REF metadata, but none was provided")

        return self.ref_metadata.get_expected_length(field_name)

    def has_ref_section(self, field_name: str) -> bool:
        """Check if a field has a corresponding section in REF."""
        if not self.ref_metadata:
            return False
        return self.ref_metadata.has_section(field_name)

    def is_meta_field(self, field_name: str) -> bool:
        """Check if field is a metadata field that should be skipped."""
        return field_name.endswith("_mode") or field_name == "line_number"

    def get_list_fields(self) -> Set[str]:
        """Get set of fields that should always be lists from configuration.

        Derives the set from fields marked with 'list_field: true' in COLUMN_CONFIG.
        """
        return {
            field_name
            for field_name, config in self.column_config.items()
            if config.get("list_field", False)
        }

    def get_bracketed_field_mapping(self) -> Dict[str, str]:
        """Build mapping from bracketed field names to internal names.

        Derives mapping from fields marked as 'bracketed: true' in config.
        Assumes internal name uses underscore format (FIELD_VALUE).
        """
        mapping = {}
        for field_name, config in self.column_config.items():
            if config.get("bracketed", False):
                # Convert FIELD_VALUE back to FIELD[VALUE] for matching
                if "_" in field_name:
                    parts = field_name.split("_", 1)
                    bracketed_name = f"{parts[0]}[{parts[1]}]"
                    mapping[bracketed_name] = field_name
        return mapping

    def get_known_fields(self) -> Set[str]:
        """Get set of all known fields including meta and generated fields.

        Generated fields are derived from bracketed field configurations
        (e.g., MACH_VEL -> mach_vel_mode).
        """
        known_meta_fields = {"line_number"}

        # Derive generated field names from bracketed fields
        known_generated_fields = set()
        for field_name, config in self.column_config.items():
            if config.get("bracketed", False):
                generated_field = f"{field_name.lower()}_mode"
                known_generated_fields.add(generated_field)

        return set(self.column_config.keys()) | known_meta_fields | known_generated_fields


class SimulationCase(BaseModel):
    """
    Main class for validation and processing of aeronautical simulation cases.

    Processes input dictionary through complete pipeline:
    1. Automatic generation of _mode fields (for bracketed fields)
    2. Individual validation using validators library
    3. Transformation using transformers library
    4. Post-validation using postvalidators library
    """

    model_config = ConfigDict(
        extra="forbid", validate_assignment=True, arbitrary_types_allowed=True
    )

    # ==== MAIN FIELDS FROM CASE CONFIGURATION ====
    RUN: Optional[int] = None
    POL: Optional[str] = None
    ACRT: Optional[str] = None
    AERODYNAMIC_CONFIGURATION: Optional[List[str]] = None
    cnfg: Optional[str] = None
    RUDDER: Optional[List[str]] = None
    ELEVON: Optional[List[str]] = None
    AILERON: Optional[List[str]] = None
    FLAP: Optional[List[str]] = None
    FANINLET: Optional[List[str]] = None
    FANOULET: Optional[List[str]] = None
    COREEXHA: Optional[List[str]] = None
    PROPELLER: Optional[List[str]] = None
    REF: Optional[str] = None
    SET: Optional[str] = None
    TURB: Optional[str] = None
    SOLVER: Optional[str] = None
    START: Optional[str] = None
    WTIME: Optional[str] = None
    CPU: Optional[int] = None
    KNITERS: Optional[List[float]] = None
    ISAD: Optional[int] = None
    GRID: Optional[List[str]] = None
    PROBES: Optional[List[str]] = None
    

    # ==== BRACKETED FIELDS (always as lists) ====
    MACH_VEL: Optional[List[float]] = None
    REY_ALT: Optional[List[float]] = None
    ALPHA_CLS: Optional[List[float]] = None
    BETA_CYS: Optional[List[float]] = None

    # ==== AUTOMATICALLY GENERATED FIELDS ====
    mach_vel_mode: Optional[str] = None
    rey_alt_mode: Optional[str] = None
    alpha_cls_mode: Optional[str] = None
    beta_cys_mode: Optional[str] = None

    # ==== METADATA ====
    line_number: Optional[int] = None

    @property
    def get_run_mode(self) -> int:
        """Get the run mode for this simulation case."""
        return self.RUN or 0

    @property
    def is_mach_sweep(self) -> bool:
        """Returns True if MACH_VEL has more than one element."""
        return bool(self.MACH_VEL) and len(self.MACH_VEL) > 1

    @property
    def is_alpha_cl_sweep(self) -> bool:
        """Returns True if ALPHA_CLS has more than one element."""
        return bool(self.ALPHA_CLS) and len(self.ALPHA_CLS) > 1

    @property
    def is_beta_cy_sweep(self) -> bool:
        """Returns True if BETA_CYS has more than one element."""
        return bool(self.BETA_CYS) and len(self.BETA_CYS) > 1
    
    @property
    def define_probes(self) -> bool:
        """ """
        return not all([aux=="-" for aux in self.PROBES])

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SimulationCase":
        """
        Main factory method to create validated object from raw dictionary.

        Args:
            data: Raw dictionary from case file (not validated)

        Returns:
            Fully validated and processed SimulationCase object

        Raises:
            CaseValidationError: If critical validation failure occurs
        """
        logger.info(f"Starting case processing - line {data.get('line_number', 'N/A')}")

        try:
            column_config = cls._load_column_config()
            validation_config = ValidationConfig(column_config, None)
            processed_data = cls._prepare_data(data, validation_config)

            # Load REF metadata if REF field is present
            ref_metadata = None
            if "REF" in processed_data and processed_data["REF"] is not None:
                ref_id = str(processed_data["REF"])
                try:
                    from app.utils.ref_parser import resolve_ref_filepath, parse_ref_file

                    ref_filepath = resolve_ref_filepath(ref_id)
                    ref_metadata = parse_ref_file(ref_filepath)
                    logger.info(f"Loaded REF metadata: {ref_metadata}")
                except FileNotFoundError as e:
                    raise CaseValidationError(f"REF file error: {str(e)}") from e
                except ValueError as e:
                    raise CaseValidationError(f"REF parsing error: {str(e)}") from e

            # Update validation_config with ref_metadata if loaded
            if ref_metadata:
                validation_config.ref_metadata = ref_metadata
            cls._validate_and_transform(processed_data, validation_config)

            logger.info("Case processed successfully")
            return cls(**processed_data)

        except Exception as e:
            logger.error(f"Critical failure in case processing: {str(e)}", exc_info=True)
            raise CaseValidationError(f"Critical validation failure: {str(e)}") from e

    @classmethod
    def _load_column_config(cls) -> Dict[str, Any]:
        """Load and validate column configuration."""
        column_config = load_config().get("COLUMN_CONFIG")
        logger.debug(f"Active configuration: {yaml.dump(column_config, indent=4, sort_keys=False)}")

        if not column_config:
            raise CaseValidationError("COLUMN_CONFIG not found in configuration")

        return column_config

    @classmethod
    def _prepare_data(cls, data: Dict[str, Any], config: ValidationConfig) -> Dict[str, Any]:
        """Prepare data for validation pipeline."""
        processed_data = data.copy()
        logger.debug(f"Original data: {processed_data}")

        processed_data = cls._map_bracketed_fields(processed_data, config)
        logger.debug(f"Mapped data: {processed_data}")

        return processed_data

    @classmethod
    def _validate_and_transform(cls, data: Dict[str, Any], config: ValidationConfig):
        """Execute complete validation and transformation pipeline."""
        cls._check_unknown_fields(data, config)
        for step_type in ["validator", "transformer", "post-validator"]:
            cls._apply_pipeline_step(data, config, step_type)
        cls._ensure_list_fields(data, config)

    @staticmethod
    def _map_bracketed_fields(data: Dict[str, Any], config: ValidationConfig) -> Dict[str, Any]:
        """Map bracketed fields from FIELD[VALUE] format to FIELD_VALUE."""
        bracketed_mapping = config.get_bracketed_field_mapping()

        for original_key, mapped_key in bracketed_mapping.items():
            if original_key in data:
                data[mapped_key] = data.pop(original_key)
                logger.debug(f"Bracketed field mapped: {original_key} -> {mapped_key}")

        return data

    @staticmethod
    def _check_unknown_fields(data: Dict[str, Any], config: ValidationConfig):
        """Check for unmapped fields in COLUMN_CONFIG and emit warnings."""
        known_fields = config.get_known_fields()

        for field_name in data.keys():
            if field_name not in known_fields:
                logger.warning(f"Unknown field found: '{field_name}' - not mapped in COLUMN_CONFIG")

    @classmethod
    def _apply_pipeline_step(
        cls,
        data: Dict[str, Any],
        config: ValidationConfig,
        step_type: str,
    ):
        """
        Generic method to apply any step of the validation pipeline.

        Args:
            data: Data dictionary being processed
            config: Validation configuration
            step_type: Type of step ('validator', 'transformer', 'post-validator')
        """
        step_mapping = PIPELINE_REGISTRY.get(step_type)
        if not step_mapping:
            raise ValueError(f"Unknown step type: {step_type}")

        for field_name, field_value in data.copy().items():
            if config.is_meta_field(field_name):
                continue

            field_config = config.get_field_config(field_name)
            if not field_config:
                continue

            step_list = field_config.get(step_type, [])

            # Normalize to list if single string
            if isinstance(step_list, str):
                step_list = [step_list]

            for step_name in step_list:
                if step_name in step_mapping:
                    cls._execute_step(
                        step_mapping[step_name], field_name, data, field_config, step_type, config
                    )

    @staticmethod
    def _execute_step(
        step_func: Callable,
        field_name: str,
        data: Dict[str, Any],
        config: Dict[str, Any],
        step_type: str,
        validation_config: "ValidationConfig",
    ):
        """
        Execute a single validation/transformation step.

        Args:
            step_func: Function to execute
            field_name: Name of the field being processed
            data: Data dictionary
            config: Field configuration
            step_type: Type of step for error messages
            validation_config: Global validation config
        """
        try:
            logger.debug(f"Executing {step_type}: {field_name} ({step_func.__name__})")

            if step_type == "validator" or step_type == "post-validator":
                # Pass validation_config to validators
                is_valid = step_func(
                    column_name=field_name,
                    data_object=data,
                    config=config,
                    validation_config=validation_config,
                )
                if not is_valid:
                    error_msg = (
                        f"{step_type.title()} failed for field '{field_name}' "
                        f"with {step_type} '{step_func.__name__}'"
                    )
                    logger.error(error_msg)
                    raise CaseValidationError(error_msg)
            else:  # transformer
                success = step_func(column_name=field_name, data_object=data, config=config)
                if not success:
                    error_msg = (
                        f"Transformation failed for field '{field_name}' "
                        f"with transformer '{step_func.__name__}'"
                    )
                    logger.error(error_msg)
                    raise CaseValidationError(error_msg)

            logger.debug(f"{step_type.title()} OK: {field_name} ({step_func.__name__})")

        except CaseValidationError:
            raise
        except Exception as e:
            error_msg = f"Error in {step_type} of field '{field_name}': {str(e)}"
            logger.critical(error_msg, exc_info=True)
            raise CaseValidationError(error_msg) from e

    # Note: Pipeline step functions are now defined in PIPELINE_REGISTRY at module level
    # for easier maintenance. See the registry definition after the imports.

    @staticmethod
    def _ensure_list_fields(data: Dict[str, Any], config: ValidationConfig):
        """Ensure that fields that should be lists are always lists, even with single elements."""
        list_fields = config.get_list_fields()

        for field_name in list_fields:
            if field_name in data and data[field_name] is not None:
                if not isinstance(data[field_name], list):
                    # Convert single value to list
                    data[field_name] = [data[field_name]]
                    logger.debug(f"Converted field '{field_name}' to list: {data[field_name]}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert validated object back to dictionary.

        Returns:
            Dictionary with processed data, ready for export
        """
        result = {}
        for field_name, field_value in self.model_dump().items():
            if field_value is not None:
                result[field_name] = field_value

        return result

    def to_yaml(self, file_path: Optional[str] = None) -> str:
        """
        Export validated object to YAML format.

        Args:
            file_path: Optional path to save file

        Returns:
            YAML string of processed object
        """
        yaml_data = self.to_dict()
        yaml_str = yaml.dump(yaml_data, default_flow_style=False, allow_unicode=True)

        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(yaml_str)
            logger.info(f"Case exported to: {file_path}")

        return yaml_str
