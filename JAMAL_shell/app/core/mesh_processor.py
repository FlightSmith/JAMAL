"""Mesh processing module for CFD simulation cases.

This module handles the generation and validation of CFD meshes using ANSA.
It processes simulation cases, prepares configuration files, executes ANSA
subprocesses, and validates the generated mesh outputs.
"""

from __future__ import annotations

import pprint
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import BaseModel, Field

from utils.process_monitoring import monitor_process_output
from utils.misc import COLORS

if TYPE_CHECKING:
    from app.core.simulation_case import SimulationCase

# LMOD module system import for Linux
try:
    sys.path.append("/lustre/lib/lmod")
    from env_modules_python import module  # pyright: ignore[reportMissingImports]
except ImportError:
    # Module only available on Linux with LMOD
    module = None  # type: ignore

logger = logging.getLogger(__name__)


class MorphMode(Enum):
    """Enum for morphing modes to improve type safety and readability."""

    NONE = 0
    MORPH_ONLY = 1
    CONTROLS_ONLY = 2
    BOTH = 3


class LogPatterns(BaseModel):
    """Log validation patterns."""

    volume_mesh_start: str = "Running volume mesh: Volume_Mesh_Scenario"
    volume_mesh_finish: str = "Time...."
    neg_vol_check: str = "Final check neg vol auto fix"
    success_patterns: list[str] = [
        "volumes meshed successfully",
        "No negative volume. Great Success!!!",
        "Fixed negative volume. Good!!!",
    ]
    failure_patterns: list[str] = [
        "volumes failed to be meshed",
        "Unfixed negative volume remains. Not good.",
    ]


class MeshProcessorConfig(BaseModel):
    """Immutable configuration for mesh processing."""
	
    model_config = {"frozen": True}

    grids_base_dir: str = Field(default="01-GRIDS")
    ansa_dir: str = Field(default="01-GRIDS/ANSA")
    mesh_output_prefix: str = Field(default="Fluent_Meters_")
    ansa_config_name: str = Field(default="ansa_config.yaml")
    mesh_file_extension: str = Field(default=".msh.h5")
    meshlog_extension: str = Field(default=".ansa.meshlog")
    ansa_geom_extension: str = Field(default=".ansa")
    ignored_extensions: list[str] = Field(default=[".ansa", ".CATPart", ".iges", ".igs"])
    warning_file: str = Field(default="warning")
    ansa_version: str = Field(default="25.2.1")
    script_dir: str = Field(default=os.path.abspath(os.path.join(os.environ.get("JAMAL_ROOT"),"bin")))
    script_basename: str = Field(default="ansamesh_script.py")
    ansa_batch_prefix: str = Field(default="run_ansa_batch")
    ansa_batch_extensions: list[str] = Field(default=[".sh", ".yaml"])
    polar_prefix: str = Field(default="POLAR-")

    max_geom_count: int = Field(default=5)
    max_trans_params: int = Field(default=12)
    max_morph_params: int = Field(default=12)

    translate_marker: str = Field(default="*t")
    morph_marker: str = Field(default="*m")
    control_surface_suffix: str = Field(default="_mcs")
    farfield_keyword: str = Field(default="FARFIELD")
    skip_value: str = Field(default="-")

    log_patterns: LogPatterns = Field(default_factory=LogPatterns)
    
    @property
    def ansa_config_full_path(self):
        return Path(self.ansa_dir) / self.ansa_config_name

class MeshProcessorError(Exception):
    """Base custom exception for mesh processing errors."""


class ValidationError(MeshProcessorError):
    """Error during mesh validation."""


class ExecutionError(MeshProcessorError):
    """Error during mesh execution."""


class MorphModeCalculator:
    """Pure logic class for morph mode calculation."""

    @staticmethod
    def calculate(morph_values: list, control_values: list) -> MorphMode:
        """Determine morph mode based on presence of values."""
        has_morph = bool(morph_values)
        has_controls = bool(control_values)
        if not has_morph and not has_controls:
            return MorphMode.NONE
        elif has_morph and not has_controls:
            return MorphMode.MORPH_ONLY
        elif not has_morph and has_controls:
            return MorphMode.CONTROLS_ONLY
        else:
            return MorphMode.BOTH


class LmodEnvironment:
    """LMOD-based environment setup for Linux/HPC."""

    def __init__(self, ansa_version: str):
        self.ansa_version = ansa_version

    def setup(self) -> None:
        """Load ANSA module."""
        if module is None:
            raise RuntimeError("LMOD module system not available (only supported on Linux)")
        module("reset")
        module("load", self.ansa_version)

    @staticmethod
    def restore(original_env: dict[str, str]) -> None:
        """Restore original environment."""
        os.environ.clear()
        os.environ.update(original_env)


class ConfigBuilder:
    """Builds configuration names and parses sections from simulation case."""

    def __init__(self, config: MeshProcessorConfig):
        self.config = config

    def parse_sections(self, case: SimulationCase) -> dict[str, list]:
        """Parse AERODYNAMIC_CONFIGURATION into sections using markers."""
        cnfg_params = case.AERODYNAMIC_CONFIGURATION or []
        sections: dict[str, list] = {
            "geometry": [],
            "translation": [],
            "morphing": [],
            "controls": [],
        }
        geom_active = True
        trans_active = False
        morph_active = False

        for param in cnfg_params:
            if param in [self.config.translate_marker, self.config.morph_marker]:
                geom_active = False
                if param == self.config.translate_marker:
                    trans_active = True
                    morph_active = False
                else:
                    trans_active = False
                    morph_active = True
                continue

            if geom_active and self.config.farfield_keyword not in param:
                sections["geometry"].append(param)
            elif trans_active:
                sections["translation"].append(int(param))
            elif morph_active:
                sections["morphing"].append(int(param))

        control_surfaces = [
            case.RUDDER or [],
            case.ELEVON or [],
            case.AILERON or [],
            case.FLAP or [],
        ]
        sections["controls"] = [
            val for surface in control_surfaces for val in surface if val != self.config.skip_value
        ]

        return sections

    def build_name(self, sections: dict[str, list]) -> str:
        """Build full config name: base_geometry + suffixes."""
        base_name = self._build_base_name(sections["geometry"])
        suffixes = self._build_suffixes(sections)
        return base_name + suffixes

    def _strip_ignored_extension(self, val: str) -> str:
        """Remove extension from val if it is in ignored_extensions."""
        ext = os.path.splitext(val)[1].lower()
        if ext in [e.lower() for e in self.config.ignored_extensions]:
            return os.path.splitext(val)[0]
        return val

    def _build_base_name(self, geometry_values: list) -> str:
        """Join geometry values with underscores as base name."""
        if not geometry_values:
            return ""
        processed_values = [self._strip_ignored_extension(val) for val in geometry_values]
        return "_".join(processed_values)

    def _build_suffixes(self, sections: dict[str, list]) -> str:
        """Append trimmed suffixes for translation, morphing, and controls."""
        suffixes = ""

        trans_values = self._trim_trailing_zeros(sections["translation"].copy())
        if trans_values:
            suffixes += "_t" + "_" + "_".join([str(x) for x in trans_values])

        morph_values = self._trim_trailing_zeros(sections["morphing"].copy())
        if morph_values:
            suffixes += "_m" + "_" + "_".join([str(x) for x in morph_values])

        control_values = self._trim_trailing_zeros(sections["controls"].copy())
        if control_values:
            suffixes += (
                self.config.control_surface_suffix
                + "_"
                + "_".join([str(x) for x in control_values])
            )

        return suffixes

    def _trim_trailing_zeros(self, values: list) -> list:
        """Trim trailing '0' values to shorten config name without info loss."""
        while values and values[-1] == 0:
            values.pop()
        return values

    def prepare_substitution_values(self, sections: dict[str, list]) -> dict[str, list]:
        """Prepare dict of values for script substitutions."""
        return {
            "geometry": sections["geometry"],
            "translation": sections["translation"],
            "morphing": sections["morphing"],
            "controls": sections["controls"],
        }


class ScriptPreparator:
    """Prepares ANSA YAML config by substituting placeholders with case values."""

    def __init__(self, config: MeshProcessorConfig):
        self.config = config
        self._morph_calculator = MorphModeCalculator()

    def _process_geometry_value(self, val: str) -> str:
        """Append ansa_geom_extension to val unless its extension is in ignored_extensions."""
        ext = os.path.splitext(val)[1].lower()
        ignored = [e.lower() for e in self.config.ignored_extensions]
        if ext not in ignored:
            return f"{val}{self.config.ansa_geom_extension}"
        return val

    def prepare_yaml_config(
        self, template_path: Path, substitution_values: dict[str, list]
    ) -> Path:
        """Load YAML template, apply substitutions, and write to ansa_config.yaml."""
        if template_path.suffix.lower() != ".yaml":
            raise ValidationError(f"Template file {template_path} must have .yaml extension")

        try:
            with open(template_path, "r") as f:
                config_dict = yaml.safe_load(f)
        except IOError as e:
            raise ValidationError(f"Failed to read YAML template {template_path}: {e}") from e

        config_dict["MAX_GEOM_COUNT"] = self.config.max_geom_count
        config_dict["geometry"] = [
            self._process_geometry_value(val) for val in substitution_values["geometry"]
        ]

        if "trans" not in config_dict:
            config_dict["trans"] = {}
        config_dict["MAX_TRANS_PARAMS"] = self.config.max_trans_params
        trans_mode = 1 if substitution_values["translation"] else 0
        config_dict["trans"]["mode"] = trans_mode
        trans_params = substitution_values["translation"][: self.config.max_trans_params]
        trans_params += [0] * (self.config.max_trans_params - len(trans_params))
        config_dict["trans"]["params"] = trans_params

        if "morph" not in config_dict:
            config_dict["morph"] = {}
        all_morph_values = substitution_values["morphing"] + substitution_values["controls"]
        morph_mode = self._morph_calculator.calculate(
            substitution_values["morphing"], substitution_values["controls"]
        ).value
        config_dict["morph"]["mode"] = morph_mode
        config_dict["MAX_MORPH_PARAMS"] = self.config.max_morph_params
        morph_params = all_morph_values[: self.config.max_morph_params]
        morph_params += [0] * (self.config.max_morph_params - len(morph_params))
        config_dict["morph"]["params"] = morph_params

        
        try:
            with open(self.config.ansa_config_full_path, "w") as f:
                yaml.dump(config_dict, f, default_flow_style=False)
        except IOError as e:
            raise ValidationError(f"Failed to write YAML config {self.config.ansa_config_full_path}: {e}") from e

        logger.debug(f"YAML config prepared at {self.config.ansa_config_full_path}")
        return self.config.ansa_config_full_path


@dataclass(frozen=True)
class RequiredFile:
    """Definition of a required output file."""

    suffix: str
    description: str


class MeshExecutor:
    """Executes the ANSA mesh generation subprocess."""

    REQUIRED_FILES: list[RequiredFile] = [
        RequiredFile(suffix=".msh.h5", description="mesh file"),
        RequiredFile(suffix=".ansa.meshlog", description="mesh log"),
    ]

    def __init__(self, config: MeshProcessorConfig):
        self.config = config
        with open(self.config.ansa_config_full_path, "r") as file_handler:
            config_dict = yaml.safe_load(file_handler)
            
        ansa_version = config_dict.get("ansa_version", self.config.ansa_version)
        #pprint.pprint(ansa_version)
        #pprint.pprint(config_dict)
        self._lmod = LmodEnvironment("ansa/" + ansa_version)


    def _build_mesh_dir(self, config_name: str) -> Path:
        """Build mesh output directory path for configuration."""
        return Path(self.config.grids_base_dir) / f"{self.config.mesh_output_prefix}{config_name}"

    def execute(self, polar_case_id: str, config_name: str, config_path: Path) -> None:
        """Execute ANSA via ansa64.sh with YAML config; skips if output exists."""
        mesh_output_dir = self._build_mesh_dir(config_name)

        logger.debug(f"Checking if mesh exists on '{mesh_output_dir}'")
        if mesh_output_dir.exists():
            msg=f"{COLORS['YELLOW']}Output mesh directory {mesh_output_dir.name} already exists for {polar_case_id}\n"\
            f"If the file mesh exist, no new mesh will be generated. The case will be submitted with the existing mesh.{COLORS['RESET']}"
            print(msg)
            return

        logger.info(f"Generating mesh for {polar_case_id}, Config: {config_name} using YAML config")

        script_path = Path(self.config.script_dir) / self.config.script_basename
        command = [
            "ansa64.sh",
            "-gui",
            "CFD",
            "-nogui",
            "-exec",
            f"load_script:'{script_path}'",
            "-exec",
            f"auto_config('{self.config.ansa_config_name}')",
        ]

        old_environ = os.environ.copy()
        try:
            self._lmod.setup()
#            process = subprocess.Popen(
#                command,
#                cwd=self.config.ansa_dir,
#                text=True,
#            )
#            process.communicate(timeout=14400)

#            monitor_process_output(
#                process,
#                inactivity_timeout=14400,
#                keywords=["ModuleNotFoundError"],
#                log_level=logging.INFO,
#                log_format="",
#            )
#
#            pprint.pprint(old_environ["PATH"])
#            logger.critical(f"Calling monitor_process_output({command})")
            rc = monitor_process_output(
                command,
                env=os.environ,
                cwd=self.config.ansa_dir,
                inactivity_timeout=14400,
                keywords=["ModuleNotFoundError"],
                log_level=logging.DEBUG,
                log_format="%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s",
#                log_format="",
            )
#            rc = process.returncode

            if rc != 0:
                raise ExecutionError(
                    f"ANSA mesh generation failed with exit code {rc} "
                    f"for {polar_case_id}, config: {config_name}"
                )

            logger.info(f"Mesh generation completed for config: {config_name}")

#        except subprocess.TimeoutExpired as e:
#            raise ExecutionError(f"Mesh generation timed out for {polar_case_id}") from e
        except Exception as e:
            if isinstance(e, ExecutionError):
                raise
            raise ExecutionError(
                f"Failed to execute mesh generation for {polar_case_id}: {e}"
            ) from e
        finally:
            self._lmod.restore(old_environ)


class MeshValidator:
    """Validates generated mesh files and logs."""

    REQUIRED_FILES: list[RequiredFile] = [
        RequiredFile(suffix=".msh.h5", description="mesh file"),
        RequiredFile(suffix=".ansa.meshlog", description="mesh log"),
    ]

    def __init__(self, config: MeshProcessorConfig):
        self.config = config

    def _build_mesh_dir(self, config_name: str) -> Path:
        """Build mesh output directory path for configuration."""
        return Path(self.config.grids_base_dir) / f"{self.config.mesh_output_prefix}{config_name}"

    def validate(self, polar_case_id: str, config_name: str) -> None:
        """Validate mesh files and log; raises ValidationError if invalid."""
        mesh_dir = self._build_mesh_dir(config_name)

        for req in self.REQUIRED_FILES:
            file_path = mesh_dir / f"{config_name}{req.suffix}"
            if not file_path.exists():
                raise ValidationError(
                    f"{req.description.capitalize()} {file_path.name} not found for {polar_case_id}"
                )

        meshlog_file = mesh_dir / f"{config_name}{self.config.meshlog_extension}"
        self._validate_mesh_log(meshlog_file, polar_case_id, config_name)

        logger.info(f"Mesh validation passed for {polar_case_id}, config: {config_name}")

    def _read_log_lines(self, meshlog_file: Path) -> list[str]:
        """Read and strip lines from the meshlog file."""
        with open(meshlog_file, "r") as f:
            return [line.strip() for line in f]

    def _check_volume_section(self, lines: list[str]) -> bool:
        """Check for volume mesh success in the log lines."""
        in_volume_section = False
        for line in lines:
            if re.search(self.config.log_patterns.volume_mesh_start, line):
                in_volume_section = True
                logger.debug(f"{self.config.log_patterns.volume_mesh_start} in line")
                continue
            if in_volume_section:
                if any(
                    re.search(pattern, line)
                    for pattern in self.config.log_patterns.success_patterns
                ):
                    logger.debug("Found success pattern")
                    return True
            if re.search(self.config.log_patterns.volume_mesh_finish, line):
                in_volume_section = False
        logger.debug("Not Found success pattern")
        return False

    def _check_neg_vol_section(
        self, lines: list[str], polar_case_id: str, config_name: str
    ) -> bool:
        """Check for negative volume success/failure in the log lines."""
        in_neg_vol_section = False
        for line in lines:
            if re.search(self.config.log_patterns.neg_vol_check, line):
                in_neg_vol_section = True
                continue
            if in_neg_vol_section:
                if any(
                    re.search(pattern, line)
                    for pattern in self.config.log_patterns.failure_patterns
                ):
                    raise ValidationError(
                        f"Negative volumes detected in mesh for {polar_case_id}, config: {config_name}"
                    )
                    return True
            if re.search(self.config.log_patterns.volume_mesh_finish, line):
                in_neg_vol_section = False
        return False

    def _validate_mesh_log(self, meshlog_file: Path, polar_case_id: str, config_name: str) -> None:
        """Validate mesh quality from log file using pattern matching."""
        lines = self._read_log_lines(meshlog_file)

        volume_success = self._check_volume_section(lines)
        if not volume_success:
            raise ValidationError(
                f"Volume mesh generation failed for {polar_case_id}, config: {config_name}"
            )

        neg_vol_success = self._check_neg_vol_section(lines, polar_case_id, config_name)
        if not neg_vol_success:
            logger.debug(f"Neg vol check inconclusive for {polar_case_id}; assuming ok")

        logger.info(f"Mesh log validation passed for {polar_case_id}, config: {config_name}")


@dataclass
class ProcessingContext:
    """Immutable context for a single case processing."""

    case: SimulationCase
    polar_case_id: str
    config_name: str | None = None
    config_path: Path | None = None


class MeshProcessingWorkflow:
    """Pure workflow orchestration."""

    def __init__(
        self,
        builder: ConfigBuilder,
        preparator: ScriptPreparator,
        executor: MeshExecutor,
        validator: MeshValidator,
    ):
        self.builder = builder
        self.preparator = preparator
        self.executor = executor
        self.validator = validator

    def execute(self, ctx: ProcessingContext) -> ProcessingContext:
        """Execute full workflow, returning updated context."""
        sections = self.builder.parse_sections(ctx.case)
        ctx.config_name = self.builder.build_name(sections)

        if not ctx.case.GRID:
            raise MeshProcessorError("Case has no GRID attribute")
        template_path = Path(ctx.case.GRID[0])
        substitution_values = self.builder.prepare_substitution_values(sections)
        ctx.config_path = self.preparator.prepare_yaml_config(template_path, substitution_values)

        self.executor.execute(ctx.polar_case_id, ctx.config_name, ctx.config_path)
        self.validator.validate(ctx.polar_case_id, ctx.config_name)

        return ctx


class MeshProcessor:
    """Processes mesh generation for CFD simulation cases."""

    def __init__(self, config: MeshProcessorConfig | None = None):
        self.config = config or MeshProcessorConfig()
        self.builder = ConfigBuilder(self.config)
        self.preparator = ScriptPreparator(self.config)
        self.executor = MeshExecutor(self.config)
        self.validator = MeshValidator(self.config)
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        Path(self.config.ansa_dir).mkdir(parents=True, exist_ok=True)
        Path(self.config.grids_base_dir).mkdir(parents=True, exist_ok=True)

    @classmethod
    def process(cls, simulation_case: SimulationCase) -> SimulationCase:
        """Main entry point for mesh processing."""
        processor = cls()
        return processor._process_case(simulation_case)

    def _process_case(self, case: SimulationCase) -> SimulationCase:
        """Process a single simulation case for mesh generation."""
        polar_case_id = self._get_case_identifier(case)
        logger.info(f"Mesh processing for {polar_case_id}")

        if not self._validate_case(case, polar_case_id):
            return case

        try:
            sections = self.builder.parse_sections(case)
            config_name = self.builder.build_name(sections)
            config_path = self._prepare_script(case, sections, config_name, polar_case_id)
            self._execute_and_update(case, polar_case_id, config_name, config_path)
            logger.info(f"Mesh processing completed successfully. Config: {config_name}")
            return case
        except (ValidationError, ExecutionError):
            raise
        except Exception as e:
            error_msg = f"Mesh processing failed for {polar_case_id}: {e}"
            logger.error(error_msg, exc_info=True)
            raise MeshProcessorError(error_msg) from e

    def _validate_case(self, case: SimulationCase, polar_case_id: str) -> bool:
        """Validate case for required attributes and ANSA processing."""
        if not hasattr(case, "GRID") or not case.GRID:
            logger.debug("No GRID parameters found, skipping mesh processing")
            return False

        grid_template = case.GRID[0]
        if not (
            grid_template.startswith(self.config.ansa_batch_prefix)
            or Path(grid_template).suffix.lower()
            in [ext.lower() for ext in self.config.ansa_batch_extensions]
        ):
            logger.debug(f"Grid parameter '{grid_template}' doesn't require ANSA batch processing")
            return False

        if not hasattr(case, "AERODYNAMIC_CONFIGURATION"):
            raise MeshProcessorError(f"No AERODYNAMIC_CONFIGURATION in case {polar_case_id}")
        return True

    def _prepare_script(
        self,
        case: SimulationCase,
        sections: dict[str, list],
        config_name: str,
        polar_case_id: str,
    ) -> Path:
        """Prepare ANSA YAML config from template and apply substitutions."""
        if not case.GRID:
            raise MeshProcessorError(f"Case {polar_case_id} has no GRID attribute")
        template_path = Path(self.config.ansa_dir) / case.GRID[0]
        if not template_path.exists():
            raise MeshProcessorError(
                f"ANSA YAML template file {case.GRID[0]} not found in {self.config.ansa_dir}"
            )

        substitution_values = self.builder.prepare_substitution_values(sections)
        return self.preparator.prepare_yaml_config(template_path, substitution_values)

    def _execute_and_update(
        self,
        case: SimulationCase,
        polar_case_id: str,
        config_name: str,
        config_path: Path,
    ) -> None:
        """Execute ANSA, validate, and update case."""
        self.executor.execute(polar_case_id, config_name, config_path)
        self.validator.validate(polar_case_id, config_name)

        case.cnfg = config_name
        if case.GRID:
            updated_grid = case.GRID.copy()
            updated_grid[0] = config_name
            case.GRID = updated_grid
        else:
            case.GRID = [config_name]

    def _get_case_identifier(self, case: SimulationCase) -> str:
        """Extract case identifier for logging and errors."""
        if not hasattr(case, "POL"):
            raise MeshProcessorError("Case missing POL attribute")
        return f"{self.config.polar_prefix}{case.POL}"
