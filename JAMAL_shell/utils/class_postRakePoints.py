#!/usr/bin/env python3
"""
Boilerplate for processing Fluent probe rake points data.

This module reads geometric definitions from `probes_rake_points` and
subsequently processes Fluent data files from `probes_*` subdirectories.
"""

# ============================================================================
# IMPORTS
# ============================================================================
import sys
import re
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.interpolate import LinearNDInterpolator  # Future use

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.path as mpath
import matplotlib.colors as mcolors
from matplotlib import colormaps

# Global logger
logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================

# File naming conventions
PROBES_RAKE_POINTS_FILENAME = "probes_rake_points"  # Main geometry file
PROBES_FOLDER_PREFIX = "probes_"  # Subdirectory prefix
DATA_FILE_EXTENSION = ".out"  # Extension for Fluent data files

PROPERTIES = ["density", "total_pressure", "velocity-magnitude", "vel_x", "vel_y", "vel_z"]  # Extend as needed

# Data file naming pattern: P_{radialIdx}_{azIdx}_{property}.out
DATA_FILE_PATTERN = "P_{radial_idx}_{az_idx}_{property}{extension}"

# Combined data file naming pattern: {property}.out (all probes in one file)
COMBINED_DATA_FILE_PATTERN = "{property}{extension}"

# Expected columns in probes_rake_points (after header)
NUM_RAKE_HEADER_LINES = 2
COLUMN_NAMES = ["radial_idx", "az_idx", "X", "Y", "Z"]

# Header line 1: num_points (azimuthal), num_radii (radial)
HEADER_NUM_POINTS_IDX = 0  # First value = azimuthal points per radius
HEADER_NUM_RADII_IDX = 1  # Second value = number of radial circles

# Header line 2: outer_radius, inner_radius
HEADER_OUTER_RADIUS_IDX = 0
HEADER_INNER_RADIUS_IDX = 1

# Points used for center calculation (indices within a radial ring)
# Using 3 points evenly spread across the azimuthal range
CENTER_CALC_NUM_POINTS = 3

# Logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_LEVEL = logging.INFO

N_AVERAGE_LAST: int = 200  # number of trailing timestep values to average
FILE_HEADER_LINES: int = 3  # non-data lines at the top of each probe file

# Default values for replacing zero density
DEFAULT_DENSITY: float = 1.225
DEFAULT_VELOCITY: float = 200.0
DEFAULT_PRESSURE: float = 101325.0

DEFAULT_PLOT_SMOOTH_LEVEL = 20
DEFAULT_PLOT_SWIRL_LEVEL = 19

DEFAULT_MAX_SWIRL = 10
DEFAULT_MIN_SWIRL = -10


# DC60 sector sweep parameters
THETA_SLICE: int = 60  # DC60 sector width [degrees]
THETA_STEP: int = 5  # sector sweep step [degrees]
THETA_SECTORS: int = 360 // THETA_STEP  # 72 total sectors

# Output directory name for plots and metrics
OUTPUT_PROBES_DIR: str = "output_probes_dir"

LABEL_MAPPING: dict = {
    "pressure": "Pressure (Pa)",
    "density": "Density (kg/m³)",
    "velocity": "Velocity (m/s)",
    "swirl": "Swirl (degrees)",
}

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================


def setup_logging(level: int = LOG_LEVEL) -> logging.Logger:
    """
    Configure the global logger for the module.

    Parameters
    ----------
    level : int
        Logging level (e.g., logging.INFO, logging.DEBUG).

    Returns
    -------
    logging.Logger
        Configured logger instance.
    """
    global logger
    logger.setLevel(level)

    # Avoid duplicate handlers if called multiple times
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


# ============================================================================
# COMMAND-LINE ARGUMENT PARSING
# ============================================================================


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns
    -------
    argparse.Namespace
        Parsed arguments with 'working_folder' and 'output' attributes.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Process Fluent probe rake points and associated data files. " "Reads geometry from 'probes_rake_points' and processes data " "from 'probes_*' subdirectories."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=("Example:\n" "  python %(prog)s /path/to/working_folder -o /path/to/output\n"),
    )

    parser.add_argument("working_folder", type=Path, help="Path to the working directory containing 'probes_rake_points' " "and 'probes_*' subdirectories.")

    parser.add_argument("-o", "--output", type=Path, default=None, help=f"Output directory for plots and metrics. " f"Defaults to '{OUTPUT_PROBES_DIR}' in working_folder.")

    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose (DEBUG) logging.")

    return parser.parse_args()


# ============================================================================
# GEOMETRY DATA STRUCTURES
# ============================================================================


class GeometryData:
    """
    Container for probe rake geometry information.

    Attributes
    ----------
    num_points : int
        Number of azimuthal points per radial index.
    num_radii : int
        Number of radial circles.
    outer_radius : float
        Radius of the outermost circle.
    inner_radius : float
        Radius of the innermost circle.
    center : np.ndarray
        3D coordinates of the circle center (shape: (3,)).
    axis : np.ndarray
        Unitary vector representing the plane normal (shape: (3,)).
    points_df : pd.DataFrame
        DataFrame with columns: radial_idx, az_idx, X, Y, Z.
    known_thetas: List[float]
        List of known thetas
    known_radii: List[float]
        List of known radii
    """

    def __init__(self):
        self.num_points: int = 0
        self.num_radii: int = 0
        self.outer_radius: float = 0.0
        self.inner_radius: float = 0.0
        self.center: Optional[np.ndarray] = None
        self.axis: Optional[np.ndarray] = None
        self.points_df: Optional[pd.DataFrame] = None
        self.known_thetas: Optional[list[float]] = None
        self.known_radii: Optional[list[float]] = None


@dataclass
class SectorResult:
    start_deg: int  # sector start angle [degrees]
    end_deg: int  # sector end angle = (start + 60) % 360
    min_pressure: float  # minimum interpolated pressure inside sector
    avg_pressure: float  # arithmetic average pressure inside sector
    avg_density: float
    avg_velocity: float
    avg_q: float  # 0.5 * rho * V^2 average
    avg_mfw_q: float  # mass-flow-weighted dynamic pressure
    avg_mass_flow: float  # rho * V average
    avg_mfw_pressure: float  # mass-flow-weighted pressure
    n_points: int  # number of interpolation points used
    # Storage for sector-contour plot
    r_points: list[float]  # radii of interpolated points
    theta_points: list[float]  # angles of interpolated points [degrees]
    pressure_points: list[float]  # pressure at each point
    avg_aip_pressure: float  # arithmetic average pressure for start angle


@dataclass
class DistortionMetrics:
    dc60_min: list[float]  # (P_avg_probes - sector_min) / q_inf,  len=72
    dc60_avg: list[float]  # (P_avg_probes - sector_avg) / q_inf,  len=72
    dc60_avg_aip: list[float]  # (P_aip_avg    - sector_avg) / Q_aip_avg, len=72
    dc60_mfw_aip: list[float]  # mass-flow-weighted variant, len=72
    IDC: float
    IDR: float
    P_avg_probes: float  # simple arithmetic avg over all raw probes
    P_avg_aip: float  # avg pressure over all interpolated sector points
    P_avg_mfw: float  # mass-flow-weighted avg pressure over all sector points
    sector_angles: list[int]  # start angles [0, 5, ..., 355]
    avg_aip: list[int]  # simple arithmetic avg over all raw probes for each angle


# ============================================================================
# GEOMETRY PARSING FUNCTIONS
# ============================================================================


def read_rake_points_file(filepath: Path) -> GeometryData:
    """
    Read and parse the probes_rake_points file.

    Parameters
    ----------
    filepath : Path
        Path to the probes_rake_points file.

    Returns
    -------
    GeometryData
        Parsed geometry data container.

    Raises
    ------
    FileNotFoundError
        If the rake points file does not exist.
    ValueError
        If the file format is invalid.
    """
    logger.info(f"Reading rake points from: {filepath}")

    if not filepath.exists():
        raise FileNotFoundError(f"Rake points file not found: {filepath}")

    geometry = GeometryData()

    with open(filepath, "r") as f:
        lines = f.readlines()

    if len(lines) < NUM_RAKE_HEADER_LINES + 1:
        raise ValueError(f"File {filepath} has insufficient lines. " f"Expected at least {NUM_RAKE_HEADER_LINES + 1}, got {len(lines)}.")

    # Parse header line 1: num_points num_radii
    header1_parts = lines[0].strip().split()
    if len(header1_parts) < 2:
        raise ValueError(f"Invalid header line 1 in {filepath}: {lines[0]}")

    geometry.num_points = int(header1_parts[HEADER_NUM_POINTS_IDX])
    geometry.num_radii = int(header1_parts[HEADER_NUM_RADII_IDX])

    # Parse header line 2: outer_radius inner_radius
    header2_parts = lines[1].strip().split()
    if len(header2_parts) < 2:
        raise ValueError(f"Invalid header line 2 in {filepath}: {lines[1]}")

    geometry.outer_radius = float(header2_parts[HEADER_OUTER_RADIUS_IDX])
    geometry.inner_radius = float(header2_parts[HEADER_INNER_RADIUS_IDX])

    logger.debug(
        f"Header parsed: num_points={geometry.num_points}, " f"num_radii={geometry.num_radii}, " f"outer_radius={geometry.outer_radius}, " f"inner_radius={geometry.inner_radius}"
    )

    # Parse data lines (starting from line index 2)
    data_lines = lines[NUM_RAKE_HEADER_LINES:]

    # Validate expected number of data lines
    expected_lines = geometry.num_radii * geometry.num_points
    if len(data_lines) < expected_lines:
        logger.warning(f"Expected {expected_lines} data lines, found {len(data_lines)}. " f"Proceeding with available data.")

    # Parse data into lists
    radial_indices = []
    az_indices = []
    x_coords = []
    y_coords = []
    z_coords = []

    for line_num, line in enumerate(data_lines, start=NUM_RAKE_HEADER_LINES + 1):
        parts = line.strip().split()
        if len(parts) < 5:
            logger.warning(f"Skipping malformed line {line_num}: {line.strip()}")
            continue

        try:
            radial_indices.append(int(parts[0]))
            az_indices.append(int(parts[1]))
            x_coords.append(float(parts[2]))
            y_coords.append(float(parts[3]))
            z_coords.append(float(parts[4]))
        except ValueError as e:
            logger.warning(f"Skipping line {line_num} due to conversion error: {e}", exc_info=True)
            continue

    # Create DataFrame with parsed data
    geometry.points_df = pd.DataFrame({"radial_idx": radial_indices, "az_idx": az_indices, "X": x_coords, "Y": y_coords, "Z": z_coords})

    # Convert index columns to proper integer type (saves memory, ensures consistency)
    geometry.points_df["radial_idx"] = geometry.points_df["radial_idx"].astype(np.int32)
    geometry.points_df["az_idx"] = geometry.points_df["az_idx"].astype(np.int32)

    logger.info(f"Parsed {len(geometry.points_df)} points " f"({geometry.num_radii} radii x {geometry.num_points} azimuthal points).")

    return geometry


def _orthonormal_basis(normal: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return two orthonormal vectors (e1, e2) spanning the plane whose normal
    is *normal*. The result is deterministic and avoids the parallel-vector edge
    case."""
    n = normal / np.linalg.norm(normal)
    candidate = np.array([1.0, 0.0, 0.0]) if abs(n[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    e1 = np.cross(n, candidate)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(n, e1)
    return e1, e2


def calculate_circle_center_3d(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> np.ndarray:
    """
    Calculate the center of a circle given three non-collinear 3D points.

    The method uses the fact that the center lies at the intersection of the
    perpendicular bisectors of the chords formed by the point pairs.
    For non-planar points, the solution gives the center of the best-fit circle
    in the least-squares sense (the unique circle passing through all three points
    in their plane).

    Parameters
    ----------
    p1, p2, p3 : np.ndarray
        3D coordinates of the three points (shape: (3,) each).

    Returns
    -------
    np.ndarray
        3D coordinates of the circle center (shape: (3,)).

    Raises
    ------
    ValueError
        If the points are collinear or nearly so.
    """
    # Vectors between points
    v1 = p2 - p1
    v2 = p3 - p1

    # Cross product gives normal to the plane
    n = np.cross(v1, v2)
    n_norm = np.linalg.norm(n)

    if n_norm < 1e-12:
        raise ValueError("Points are collinear or nearly so; center is undefined.")

    # Unit normal
    n_unit = n / n_norm

    # Project points onto the plane perpendicular to n
    # by removing the component along n
    def project_to_plane(point: np.ndarray) -> np.ndarray:
        return point - np.dot(point - p1, n_unit) * n_unit

    q1 = project_to_plane(p1)
    q2 = project_to_plane(p2)
    q3 = project_to_plane(p3)

    # In the plane, find circle center using 2D method
    # (perpendicular bisector intersection)
    # Work in coordinates where n_unit is aligned with z-axis
    # Use Gram-Schmidt to create plane basis

    # Choose an arbitrary vector not parallel to n_unit
    if abs(n_unit[0]) < 0.9:
        ref = np.array([1.0, 0.0, 0.0])
    else:
        ref = np.array([0.0, 1.0, 0.0])

    # First basis vector (in-plane)
    e1 = np.cross(n_unit, ref)
    e1 = e1 / np.linalg.norm(e1)

    # Second basis vector (completes right-handed system)
    e2 = np.cross(n_unit, e1)
    e2 = e2 / np.linalg.norm(e2)

    # Transform 2D points
    def to_2d(point: np.ndarray) -> np.ndarray:
        return np.array([np.dot(point, e1), np.dot(point, e2)])

    q1_2d = to_2d(q1)
    q2_2d = to_2d(q2)
    q3_2d = to_2d(q3)

    # 2D circle center calculation
    # Perpendicular bisector of (q1, q2): mid1 + t1 * perp(v1)
    mid1 = (q1_2d + q2_2d) / 2.0
    v1_2d = q2_2d - q1_2d
    perp1 = np.array([-v1_2d[1], v1_2d[0]])  # 90° rotation

    # Perpendicular bisector of (q1, q3): mid2 + t2 * perp(v2)
    mid2 = (q1_2d + q3_2d) / 2.0
    v2_2d = q3_2d - q1_2d
    perp2 = np.array([-v2_2d[1], v2_2d[0]])  # 90° rotation

    # Solve for intersection: mid1 + t1*perp1 = mid2 + t2*perp2
    # In matrix form: perp1 * t1 - perp2 * t2 = mid2 - mid1
    A = np.column_stack([perp1, -perp2])
    b = mid2 - mid1

    det = A[0, 0] * A[1, 1] - A[0, 1] * A[1, 0]
    if abs(det) < 1e-12:
        raise ValueError("Points are collinear in projected 2D plane.")

    t = np.linalg.solve(A, b)

    # Center in 2D
    center_2d = mid1 + t[0] * perp1

    # Transform back to 3D
    center_3d = center_2d[0] * e1 + center_2d[1] * e2 + np.dot(p1, n_unit) * n_unit

    return center_3d, n_unit  # (center, unit_normal_to_plane)


def compute_center(points_df: pd.DataFrame, radial_idx: int = 1) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute the geometric center of the concentric circles.

    Uses three points from the specified radial index to determine the circle
    center. This works for circles in any plane.

    Parameters
    ----------
    points_df : pd.DataFrame
        DataFrame with columns: radial_idx, az_idx, X, Y, Z.
    radial_idx : int, optional
        Radial index to use for center calculation. Default is 1 (outermost).
        Must exist in points_df.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        3D coordinates of the center and axis (shape: (3,)) each.

    Raises
    ------
    ValueError
        If the radial_idx is not found or insufficient points exist.
    """
    # Filter points for the specified radial index
    ring_points = points_df[points_df["radial_idx"] == radial_idx]

    if len(ring_points) < 3:
        raise ValueError(f"Radial index {radial_idx} has only {len(ring_points)} points. " f"At least 3 are required for center calculation.")

    # Select 3 evenly-spaced points from the ring
    step = len(ring_points) // CENTER_CALC_NUM_POINTS
    indices = [
        ring_points.index[0],
        ring_points.index[step],
        ring_points.index[2 * step],
    ]

    p1 = ring_points.loc[indices[0], ["X", "Y", "Z"]].values.astype(np.float64)
    p2 = ring_points.loc[indices[1], ["X", "Y", "Z"]].values.astype(np.float64)
    p3 = ring_points.loc[indices[2], ["X", "Y", "Z"]].values.astype(np.float64)

    logger.debug(f"Using points for center calculation (radial_idx={radial_idx}):\n" f"  P1: {p1}\n" f"  P2: {p2}\n" f"  P3: {p3}")

    try:
        center, axis = calculate_circle_center_3d(p1, p2, p3)

        # Enforce aft-pointing convention: X-component of axis must be positive
        AFT_AXIS = np.array([1.0, 0.0, 0.0])
        if np.dot(axis, AFT_AXIS) < 0:
            axis = -axis

        logger.info(f"Circle center computed: {center}")
        return center, axis
    except ValueError as e:
        logger.error(f"Failed to compute center: {e}", exc_info=True)
        raise


def snap_to_ring(r_array, known_rings, tol=1e-4):
    r_snapped = r_array.copy()
    for ring_r in known_rings:
        close = np.abs(r_array - ring_r) < tol
        r_snapped[close] = ring_r
    return r_snapped


def calculate_swirl(df: pd.DataFrame) -> pd.DataFrame:
    pass


def build_interpolators(
    df: pd.DataFrame,
    geometry: GeometryData,
) -> tuple[dict[str, LinearNDInterpolator], float]:
    """
    Build LinearNDInterpolator objects for pressure, density, and velocity.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with processed probe data including plane_u, plane_v, R columns.
    geometry : GeometryData
        Geometry information containing center and axis.

    Returns
    -------
    tuple[dict[str, LinearNDInterpolator], float]
        Dictionary of interpolators and p_avg_fallback value.
    """

    theta_deg = df["theta"] % 360
    r_vals = df["R"].values

    interpolators: dict[str, LinearNDInterpolator] = {}
    properties = ["pressure", "density", "velocity"]

    for prop in properties:
        prop_vals = df[prop].values

        r_aug = np.concatenate([r_vals, r_vals, r_vals])
        theta_aug = np.concatenate([theta_deg - 360.0, theta_deg, theta_deg + 360.0])
        values_aug = np.concatenate([prop_vals, prop_vals, prop_vals])

        points = np.column_stack([r_aug, theta_aug])
        interpolators[prop] = LinearNDInterpolator(
            points,
            values_aug,
            rescale=True,
        )

    p_avg_fallback = float(df["pressure"].mean())

    return interpolators, p_avg_fallback


def compute_sector_sweep_fast(
    interpolators: dict[str, "LinearNDInterpolator"],
    radial_points: np.ndarray,
    p_avg_fallback: float = DEFAULT_PRESSURE,
    log_warnings: bool = True,
) -> tuple[list[SectorResult], pd.DataFrame]:
    """
    High-performance sector sweep using vectorized operations.
    """
    # Generate grid
    grid_df = generate_interpolation_grid(radial_points)

    # Interpolate once
    grid_df = interpolate_grid(grid_df, interpolators, p_avg_fallback, log_warnings)

    # For each point, determine which sector(s) it belongs to
    all_starts = np.arange(0, 360, THETA_STEP)
    theta_slice = THETA_SLICE

    # Create sector assignments for each point
    sector_masks = []
    for start in all_starts:
        end = (start + theta_slice) % 360
        if end > start:
            mask = (grid_df["theta"] >= start) & (grid_df["theta"] < end)
        else:
            mask = (grid_df["theta"] >= start) | (grid_df["theta"] < end)
        sector_masks.append(mask)

    # Build results using aggregation
    results = []

    for i, start in enumerate(all_starts):
        sector_df = grid_df[sector_masks[i]].copy()
        n_points = len(sector_df)

        if n_points == 0:
            results.append(_empty_sector_result(start))
            continue

        # Pre-computed aggregations
        sum_mass_flow = sector_df["mass_flow"].sum()

        # Get arrays for plotting
        r_points = sector_df["R"].tolist()
        theta_points = sector_df["theta"].tolist()
        pressure_points = sector_df["pressure"].tolist()

        # Start angle average
        start_angle_mask = sector_masks[i] & (grid_df["theta"] == start)
        avg_aip = grid_df.loc[start_angle_mask, "pressure"].mean()

        results.append(
            SectorResult(
                start_deg=start,
                end_deg=(start + THETA_SLICE) % 360,
                min_pressure=sector_df["pressure"].min(),
                avg_pressure=sector_df["pressure"].mean(),
                avg_density=sector_df["density"].mean(),
                avg_velocity=sector_df["velocity"].mean(),
                avg_q=sector_df["q"].mean(),
                avg_mfw_q=sector_df["mass_flow_q"].sum() / sum_mass_flow if sum_mass_flow > 0 else 0.0,
                avg_mass_flow=sum_mass_flow / n_points,
                avg_mfw_pressure=sector_df["mass_flow_pressure"].sum() / sum_mass_flow if sum_mass_flow > 0 else 0.0,
                n_points=n_points,
                r_points=r_points,
                theta_points=theta_points,
                pressure_points=pressure_points,
                avg_aip_pressure=avg_aip if not np.isnan(avg_aip) else sector_df["pressure"].mean(),
            )
        )

    return results, grid_df


def _empty_sector_result(start_deg: int) -> SectorResult:
    return SectorResult(
        start_deg=start_deg,
        end_deg=(start_deg + THETA_SLICE) % 360,
        min_pressure=0.0,
        avg_pressure=0.0,
        avg_density=0.0,
        avg_velocity=0.0,
        avg_q=0.0,
        avg_mfw_q=0.0,
        avg_mass_flow=0.0,
        avg_mfw_pressure=0.0,
        n_points=0,
        r_points=[],
        theta_points=[],
        pressure_points=[],
        avg_aip_pressure=0.0,
    )


def compute_ring_averages(
    df: pd.DataFrame,
    geometry: GeometryData,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute per-ring average and minimum pressure values.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with probe data including radial_idx and pressure columns.
    geometry : GeometryData
        Geometry information.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        Arrays of ring average pressure and ring minimum pressure.
    """
    ring_avg_pressure = np.zeros(geometry.num_radii)
    ring_min_pressure = np.zeros(geometry.num_radii)

    for radial_idx in range(1, geometry.num_radii + 1):
        ring_data = df[df["radial_idx"] == radial_idx]
        if not ring_data.empty:
            ring_avg_pressure[radial_idx - 1] = ring_data["pressure"].mean()
            ring_min_pressure[radial_idx - 1] = ring_data["pressure"].min()
        else:
            logger.warning(f"No data found for radial_idx {radial_idx}")

    return ring_avg_pressure, ring_min_pressure


def compute_distortion_metrics(
    sector_results: list[SectorResult],
    ring_avg: np.ndarray,
    ring_min: np.ndarray,
    avg_pressure: float,
    avg_density: float,
    avg_velocity: float,
) -> DistortionMetrics:
    """
    Compute distortion metrics including DC60 variants, IDC, and IDR.

    Parameters
    ----------
    sector_results : list[SectorResult]
        Results from sector sweep.
    ring_avg : np.ndarray
        Per-ring average pressures.
    ring_min : np.ndarray
        Per-ring minimum pressures.
    avg_pressure : float
        Global average pressure over all probes.
    avg_density : float
        Global average density over all probes.
    avg_velocity : float
        Global average velocity over all probes.

    Returns
    -------
    DistortionMetrics
        Complete distortion metrics.
    """
    q_inf = 0.5 * avg_density * avg_velocity**2

    # Compute sector-averaged quantities across all sectors
    total_p_aip = 0.0
    total_q_aip = 0.0
    total_mfw_p = 0.0
    total_mass_flow = 0.0
    sector_angles = []

    dc60_min = []
    dc60_avg = []
    dc60_avg_aip = []
    dc60_mfw_aip = []
    avg_aip = []

    for sector in sector_results:
        sector_angles.append(sector.start_deg)

        # DC60 based on probe averages
        dc60_min.append((avg_pressure - sector.min_pressure) / q_inf)
        dc60_avg.append((avg_pressure - sector.avg_pressure) / q_inf)

        avg_aip.append(sector.avg_aip_pressure)

        # Accumulate for AIP-averaged quantities
        total_p_aip += sector.avg_pressure * sector.n_points
        total_q_aip += sector.avg_q * sector.n_points
        total_mfw_p += sector.avg_mfw_pressure * sector.avg_mass_flow * sector.n_points
        total_mass_flow += sector.avg_mass_flow * sector.n_points

    # Compute AIP-averaged quantities
    total_points = sum(sector.n_points for sector in sector_results)
    P_avg_aip = total_p_aip / total_points
    Q_avg_aip = total_q_aip / total_points
    P_avg_mfw = total_mfw_p / total_mass_flow if total_mass_flow > 0 else 0.0

    # Compute DC60 variants using AIP averages
    for sector in sector_results:
        dc60_avg_aip.append((P_avg_aip - sector.avg_pressure) / Q_avg_aip)
        dc60_mfw_aip.append((P_avg_mfw - sector.avg_mfw_pressure) / (0.5 * avg_density * avg_velocity**2))

    # Compute IDC and IDR (per ring pair)
    num_rings = len(ring_avg)
    idc_values = []
    idr_values = []

    for i in range(num_rings - 1):
        # IDC: average of distortions at adjacent rings
        idc_i = 0.5 * ((avg_pressure - ring_min[i]) / avg_pressure + (avg_pressure - ring_min[i + 1]) / avg_pressure)
        idc_values.append(idc_i)

        # IDR: radial distortion between adjacent rings
        idr_i = (avg_pressure - ring_avg[i]) / avg_pressure
        idr_values.append(idr_i)

    # Handle the last ring for IDR (use the outermost ring)
    if num_rings > 0:
        idr_last = (avg_pressure - ring_avg[-1]) / avg_pressure
        idr_values.append(idr_last)

    IDC = max(idc_values) if idc_values else 0.0
    IDR = max(idr_values[0], idr_values[-1]) if idr_values else 0.0

    return DistortionMetrics(
        dc60_min=dc60_min,
        dc60_avg=dc60_avg,
        dc60_avg_aip=dc60_avg_aip,
        dc60_mfw_aip=dc60_mfw_aip,
        IDC=IDC,
        IDR=IDR,
        P_avg_probes=avg_pressure,
        P_avg_aip=P_avg_aip,
        P_avg_mfw=P_avg_mfw,
        sector_angles=sector_angles,
        avg_aip=avg_aip,
    )


def generate_interpolation_grid(
    radial_points: np.ndarray,
    theta_start: int = 0,
    theta_end: int = 360,
    theta_step: int = THETA_STEP,
) -> pd.DataFrame:
    """
    Generate a grid of (r, theta) points for interpolation.

    Returns a DataFrame with one row per (r, theta) combination,
    ready for bulk interpolation.
    """
    theta_points = np.arange(theta_start, theta_end, theta_step)

    # Create grid using cross join pattern
    n_r = len(radial_points)
    n_theta = len(theta_points)

    # Tile and repeat to create all combinations
    df = pd.DataFrame(
        {
            "R": np.tile(radial_points, n_theta),
            "theta": np.repeat(theta_points, n_r),
        }
    )

    # Add polar coordinates
    df["x_plot"] = df["R"] * np.cos(np.radians(df["theta"] + 90))
    df["y_plot"] = df["R"] * np.sin(np.radians(df["theta"] + 90))

    return df


def interpolate_grid(
    df: pd.DataFrame,
    interpolators: dict[str, "LinearNDInterpolator"],
    p_avg_fallback: float = DEFAULT_PRESSURE,
    default_density: float = DEFAULT_DENSITY,
    default_velocity: float = DEFAULT_VELOCITY,
    log_warnings: bool = True,
) -> pd.DataFrame:
    """
    Interpolate all properties for each point in the grid.
    Handles NaN values with fallbacks.
    """
    df = df.copy()

    # Interpolate all at once
    df["pressure"] = interpolators["pressure"]((df["R"], df["theta"]))
    df["density"] = interpolators["density"]((df["R"], df["theta"]))
    df["velocity"] = interpolators["velocity"]((df["R"], df["theta"]))

    # Track NaN counts for logging
    nan_pressure_mask = df["pressure"].isna()
    nan_density_mask = df["density"].isna()
    nan_velocity_mask = df["velocity"].isna()

    if log_warnings and nan_pressure_mask.any():
        logger.warning(f"NaN pressure at {nan_pressure_mask.sum()} points, " f"using fallback {p_avg_fallback:.1f}")

    # Apply fallbacks
    df["pressure"] = df["pressure"].fillna(p_avg_fallback)
    df["density"] = df["density"].fillna(default_density)
    df["velocity"] = df["velocity"].fillna(default_velocity)

    # Pre-compute derived quantities (calculated once, used many times)
    df["mass_flow"] = df["density"] * df["velocity"]
    df["q"] = 0.5 * df["density"] * df["velocity"] ** 2
    df["mass_flow_q"] = df["mass_flow"] * df["q"]
    df["mass_flow_pressure"] = df["mass_flow"] * df["pressure"]

    return df


def plot_sector_contour(
    grid_df: pd.DataFrame,
    output_dir: Path,
    geometry: GeometryData,
    theta_step: int = THETA_STEP,
    theta_slice: int = THETA_SLICE,
) -> None:
    """
    Generate contour plots for each sector showing pressure distribution.

    Uses a pre-computed grid DataFrame with interpolated values, avoiding
    redundant interpolation. All sectors use the same global pressure
    colour scale (p_min … p_max) for direct comparability.

    Parameters
    ----------
    grid_df : pd.DataFrame
        Pre-computed grid containing columns: 'R', 'theta', 'pressure',
        'density', 'velocity', etc. for all sector points.
    output_dir : Path
        Directory to save the plots.
    geometry : GeometryData
        Geometry information for coordinate transformation.
    theta_step : int
        Angular step between sectors (degrees). Default: 5.
    theta_slice : int
        Angular width of each sector (degrees). Default: 60.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    center_x, center_y, center_z = geometry.center
    sector_starts = list(range(0, 360, theta_step))

    # Pre-compute Cartesian coordinates for the entire grid (once!)
    grid_df = grid_df.copy()

    if center_y < 0:
        fuselage_label = "← fuselage"
    elif center_y > 0:
        fuselage_label = "fuselage →"
    else:
        fuselage_label = "→ fuselage ←"

    for sector_idx, min_angle in enumerate(sector_starts):
        max_angle = (min_angle + theta_slice) % 360

        # Filter points belonging to this sector (vectorized)
        sector_mask = _get_sector_mask(grid_df["theta"], min_angle, max_angle + theta_step)
        sector_df = grid_df[sector_mask]

        if len(sector_df) == 0:
            logger.warning(f"No points in sector {min_angle}°")
            continue

        tolerance: float = 1e-8
        inner_radius = sector_df["R"].min()
        outer_radius = sector_df["R"].max()

        logger.debug(f"Radius range: {inner_radius} → {outer_radius}")
        logger.debug(f"Angle range: {min_angle} → {max_angle}")

        # --- Select boundary segments ---
        # Workaround for wrapping values over 360 making the arc traversal order consistent
        arc_sort = lambda df, asc: (df.assign(_t=(df["theta"] - min_angle) % 360).sort_values("_t", ascending=asc).drop(columns="_t"))

        outer_arc_df = arc_sort(sector_df[np.isclose(sector_df["R"], outer_radius, atol=tolerance)], True)
        inner_arc_df = arc_sort(sector_df[np.isclose(sector_df["R"], inner_radius, atol=tolerance)], False)
        max_angle_edge_df = sector_df[np.isclose(sector_df["theta"], max_angle, atol=tolerance)].sort_values("R", ascending=False)
        min_angle_edge_df = sector_df[np.isclose(sector_df["theta"], min_angle, atol=tolerance)].sort_values("R", ascending=True)
        # --- Concatenate in correct traversal order ---
        boundary_df = pd.concat([outer_arc_df, max_angle_edge_df, inner_arc_df, min_angle_edge_df], ignore_index=True)

        # --- Convert to vertices ---
        vertices = boundary_df[["x_plot", "y_plot"]].to_numpy()

        if len(vertices) == 0:
            raise ValueError("No boundary points found. Check input data or tolerance.")

        # --- Close polygon explicitly ---
        path = mpath.Path(vertices)

        # Extract coordinates and pressure
        x_plot_coords = sector_df["x_plot"].values
        y_plot_coords = sector_df["y_plot"].values
        pressure_values = sector_df["pressure"].values

        # Plot
        fig, ax = plt.subplots(figsize=(8, 8))

        before = set(ax.get_children())

        levels = DEFAULT_PLOT_SMOOTH_LEVEL
        contour = ax.tricontourf(
            x_plot_coords,
            y_plot_coords,
            pressure_values,
            levels=levels,
            cmap="plasma",
            vmin=grid_df["pressure"].min(),
            vmax=grid_df["pressure"].max(),
        )

        plt.colorbar(contour, ax=ax, label="Pressure")

        patch = mpatches.PathPatch(path, facecolor="none", edgecolor="none")
        ax.add_patch(patch)

        # Clip only the artists that tricontourf just added
        after = set(ax.get_children())
        for artist in after - before:
            if hasattr(artist, "set_clip_path"):
                artist.set_clip_path(patch)

        # Overlay points as circles
        ax.scatter(
            x_plot_coords,
            y_plot_coords,
            color="black",
            s=30,
            edgecolors="white",
            zorder=3,
        )

        # Axis limits: always include the duct centre
        radius_outter = sector_df["R"].max()

        def remap_interval(lim_lo: float, lim_hi: float, R: float, center: float = 0):
            if lim_lo > center:
                return center, R
            if lim_hi < center:
                return -R, center

            total = abs(lim_lo) + lim_hi
            return (-R * abs(lim_lo) / total, R * lim_hi / total) if total else (-R / 2, R / 2)

        x_plot_lo, x_plot_hi = remap_interval(x_plot_coords.min(), x_plot_coords.max(), radius_outter, 0)
        y_plot_lo, y_plot_hi = remap_interval(y_plot_coords.min(), y_plot_coords.max(), radius_outter, 0)

        pad_x = (x_plot_hi - x_plot_lo) * 0.07
        pad_y = (y_plot_hi - y_plot_lo) * 0.07
        xlim_min, xlim_max = (x_plot_lo - pad_x, x_plot_hi + pad_x)
        ylim_min, ylim_max = (y_plot_lo - pad_y, y_plot_hi + pad_y)
        ax.set_xlim(xlim_min, xlim_max)
        ax.set_ylim(ylim_min, ylim_max)

        # Invert x-axis: Y+ (starboard) appears on the LEFT — pilot-eye view
        ax.invert_xaxis()
        ax.set_title(f"Sector {min_angle:03d}° - {max_angle:03d}°", y=1.05, fontsize=12, pad=15)
        ax.set_xlabel(f"Y  [m] ({fuselage_label})")
        ax.set_ylabel("Z  [m]")
        ax.set_aspect("equal")

        # Display unitary vector components (u,v,w)
        u, v, w = geometry.axis
        extra_info_msg = f"plane normal  ({u:.2f}, {v:.2f}, {w:.2f})      Probes geometric center  ({center_x:.2f}, {center_y:.2f}, {center_z:.2f})"
        ax.text(0.5, 1.02, extra_info_msg, transform=ax.transAxes, ha="center", va="bottom", fontsize=6, color="black")

        filename = f"sector_{min_angle:03d}.pdf"
        fig.savefig(str(output_dir / filename), bbox_inches="tight")
        plt.close(fig)

        logger.info(f"Saved sector contour plot: {output_dir / filename}")


def _get_sector_mask(
    theta_series: pd.Series,
    start_deg: int,
    end_deg: int,
) -> pd.Series:
    """
    Vectorized sector membership check with wrap-around support.

    Parameters
    ----------
    theta_series : pd.Series
        Series of angles in degrees.
    start_deg : int
        Sector start angle.
    end_deg : int
        Sector end angle (exclusive).

    Returns
    -------
    pd.Series
        Boolean mask indicating which points belong to the sector.
    """
    if end_deg > start_deg:
        # Normal sector (no wrap-around)
        return (theta_series >= start_deg) & (theta_series < end_deg)
    else:
        # Wrapping sector (e.g., 340° - 40°)
        return (theta_series >= start_deg) | (theta_series < end_deg)


def plot_dc60(metrics: DistortionMetrics, output_dir: Path) -> None:
    """
    Generate DC60 line chart plots.

    Parameters
    ----------
    metrics : DistortionMetrics
        Computed distortion metrics.
    output_dir : Path
        Directory to save the plots.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Plot configurations
    plot_configs = [
        ("DC60_min.pdf", "DC60 Minimum", metrics.dc60_min),
        ("DC60_avg.pdf", "DC60 Average", metrics.dc60_avg),
        ("DC60_avg_aip.pdf", "DC60 Average AIP", metrics.dc60_avg_aip),
        ("DC60_mfw_aip.pdf", "DC60 Mass-Flow Weighted AIP", metrics.dc60_mfw_aip),
        ("AVG_PRESSURE.pdf", "Average pressure", metrics.avg_aip),
    ]

    for filename, title, values in plot_configs:
        fig, ax = plt.subplots(figsize=(10, 6))

        ax.plot(metrics.sector_angles, values, "b-", linewidth=2, marker="o", markersize=4)
        ax.set_xlabel("Sector Start Angle [degrees]")
        ax.set_ylabel("DC60")
        ax.set_title(title)
        ax.grid(True, alpha=0.3)

        # Set x-axis ticks every 30 degrees
        ax.set_xticks(range(0, 360, 30))

        plt.tight_layout()
        fig.savefig(str(output_dir / filename), bbox_inches="tight")
        plt.close(fig)

        logger.info(f"Saved DC60 plot: {output_dir / filename}")


# ============================================================================
# FOLDER DISCOVERY
# ============================================================================


def find_probes_folders(working_folder: Path) -> List[Path]:
    """
    Find all immediate subdirectories starting with PROBES_FOLDER_PREFIX.

    Parameters
    ----------
    working_folder : Path
        Path to the working directory.

    Returns
    -------
    List[Path]
        List of paths to probes_* subdirectories.
    """
    if not working_folder.is_dir():
        raise NotADirectoryError(f"Working folder is not a directory: {working_folder}")

    probes_folders = sorted([d for d in working_folder.iterdir() if d.is_dir() and d.name.startswith(PROBES_FOLDER_PREFIX)])

    logger.info(f"Found {len(probes_folders)} folders matching '{PROBES_FOLDER_PREFIX}*': " f"{[d.name for d in probes_folders]}")

    return probes_folders


# ============================================================================
# DATA FILE PROCESSING (PLACEHOLDER FOR FUTURE IMPLEMENTATION)
# ============================================================================


def build_data_filename(radial_idx: int, az_idx: int, property_name: str) -> str:
    """
    Build the data filename for a specific point and property.

    .. deprecated::
        This function is deprecated. The new format uses combined files
        (one file per property with all probes). Use ``parse_combined_probe_file``
        and ``COMBINED_DATA_FILE_PATTERN`` instead.

    Parameters
    ----------
    radial_idx : int
        Radial index (1-based).
    az_idx : int
        Azimuthal index (1-based).
    property_name : str
        Property name (e.g., 'density', 'pressure').

    Returns
    -------
    str
        Filename string (e.g., 'P_1_2_density.out').
    """
    return DATA_FILE_PATTERN.format(radial_idx=radial_idx, az_idx=az_idx, property=property_name, extension=DATA_FILE_EXTENSION)


# ============================================================================
# MAIN PROCESSING FUNCTION (SKELETON FOR FUTURE IMPLEMENTATION)
# ============================================================================


def parse_probe_file(filepath: Path) -> float | None:
    """Parse a single probe output file.

    .. deprecated::
        This function is deprecated. The new format uses combined files
        (one file per property with all probes). Use ``parse_combined_probe_file``
        instead.

    Skips the first ``FILE_HEADER_LINES`` lines, then reads rows of the form
    ``<step> <value>``.  Returns the mean of the last ``N_AVERAGE_LAST`` values,
    or ``None`` when the file is unreadable or contains no valid rows.
    """
    values: list[float] = []
    try:
        with filepath.open("r") as fh:
            for lineno, line in enumerate(fh):
                if lineno < FILE_HEADER_LINES:
                    continue
                parts = line.split()
                if len(parts) != 2:
                    continue
                try:
                    values.append(float(parts[1]))
                except ValueError:
                    logger.debug(
                        "Skipping non-numeric value at line %d of %s",
                        lineno + 1,
                        filepath,
                    )
    except OSError as exc:
        logger.error("Cannot read probe file %s: %s", filepath, exc, exc_info=True)
        return None

    if not values:
        logger.warning("No valid data rows found in %s", filepath)
        return None

    tail = values[-N_AVERAGE_LAST:]
    logger.debug("Averaging %d values (of %d) from %s", len(tail), len(values), filepath)
    return float(np.mean(tail))


def parse_combined_probe_file(filepath: Path) -> dict[tuple[int, int], float | None]:
    """Parse a combined probe output file containing all probes for one property.

    The file has 3 header lines. Line 3 contains column headers like
    ``"pt(p_1_1)" "pt(p_1_2)" ...`` which identify each probe by its
    ``(radial_idx, az_idx)`` coordinates.

    Reads all data rows (iteration + one column per probe), accumulates values
    per column, then returns the mean of the last ``N_AVERAGE_LAST`` values
    for each probe.

    Parameters
    ----------
    filepath : Path
        Path to the combined probe file (e.g., ``total_pressure.out``).

    Returns
    -------
    dict[tuple[int, int], float | None]
        Mapping from ``(radial_idx, az_idx)`` to the time-averaged value,
        or ``None`` if the probe column had no valid data.
    """
    try:
        with filepath.open("r") as fh:
            lines = fh.readlines()
    except OSError as exc:
        logger.error("Cannot read combined probe file %s: %s", filepath, exc, exc_info=True)
        return {}

    if len(lines) <= FILE_HEADER_LINES:
        logger.warning("Combined probe file has no data rows: %s", filepath)
        return {}

    # Parse column headers from line 3 (index 2)
    header_line = lines[2]
    # Match tokens like "pt(p_1_1)" or "density(p_2_3)"
    col_map: dict[int, tuple[int, int]] = {}  # column_index -> (radial_idx, az_idx)

    for col_idx, token in enumerate(header_line.split()):
        match = re.search(r"p_(\d+)_(\d+)", token)
        if match:
            radial_idx = int(match.group(1))
            az_idx = int(match.group(2))
            col_map[col_idx] = (radial_idx, az_idx)

    if not col_map:
        logger.warning("No probe columns found in header of %s", filepath)
        return {}

    # Accumulate values per probe column (skip first column which is iteration)
    # Start from column 1 since column 0 is the iteration number
    probe_values: dict[tuple[int, int], list[float]] = {key: [] for key in col_map.values()}

    for line in lines[FILE_HEADER_LINES:]:
        parts = line.split()
        if len(parts) < 2:
            continue
        for col_idx, (radial_idx, az_idx) in col_map.items():
            if col_idx < len(parts):
                try:
                    probe_values[(radial_idx, az_idx)].append(float(parts[col_idx]))
                except ValueError:
                    logger.debug(
                        "Skipping non-numeric value at column %d in %s",
                        col_idx + 1,
                        filepath,
                    )

    # Compute mean of last N_AVERAGE_LAST values for each probe
    result: dict[tuple[int, int], float | None] = {}
    for (radial_idx, az_idx), values in probe_values.items():
        if not values:
            result[(radial_idx, az_idx)] = None
        else:
            tail = values[-N_AVERAGE_LAST:]
            logger.debug(
                "Averaging %d values (of %d) for probe (%d, %d) from %s",
                len(tail),
                len(values),
                radial_idx,
                az_idx,
                filepath,
            )
            result[(radial_idx, az_idx)] = float(np.mean(tail))

    return result


def process_probes_folder(
    probes_folder: Path,
    geometry: GeometryData,
) -> pd.DataFrame:
    """Augment *df* with cylindrical coordinates and time-averaged property values.

    Parameters
    ----------
    probes_folder:
        Directory containing files named ``P_<radial_idx>_<az_idx>_<property>.out``.
    geometry:
        Parsed geometry data container

    Returns
    -------
    pd.DataFrame
        Copy of *df* with new columns ``R``, ``theta`` (degrees, range −180…180),
        and one column per entry in ``PROPERTIES``.
    """
    axis = geometry.axis
    center = geometry.center
    df = geometry.points_df

    axis = axis / np.linalg.norm(axis)
    e1, e2 = _orthonormal_basis(axis)

    df = df.copy()

    # ── Cylindrical coordinates ────────────────────────────────────────────
    coords = df[["X", "Y", "Z"]].to_numpy()  # (N, 3)
    v = coords - center  # vectors from centre
    v_axial = np.outer(v @ axis, axis)  # component along axis. @ operator is dot product
    v_radial = v - v_axial  # in-plane component

    df["R"] = np.linalg.norm(v_radial, axis=1)

    raw_theta = np.degrees(np.arctan2(v_radial @ e2, v_radial @ e1))

    theta_fixed = raw_theta - raw_theta[0]
    df["theta"] = np.round(theta_fixed, 3) % 360

    # with pd.option_context("display.max_rows", None, "display.max_columns", None, "display.width", 1000):
    #     print(df["theta"])
    #     sys.exit()

    df["plane_u"] = v_radial @ e1
    df["plane_v"] = v_radial @ e2

    # ── Property files (combined format: one file per property) ────────────

    for prop in PROPERTIES:
        combined_file = probes_folder / COMBINED_DATA_FILE_PATTERN.format(property=prop, extension=DATA_FILE_EXTENSION)
        if not combined_file.is_file():
            logger.warning("Missing combined probe file: %s", combined_file)
            df[prop] = None
            continue

        probe_values = parse_combined_probe_file(combined_file)
        df[prop] = [probe_values.get((int(row["radial_idx"]), int(row["az_idx"]))) for _, row in df.iterrows()]

    df.rename(columns={"total_pressure": "pressure", "velocity-magnitude": "velocity"}, inplace=True)

    # Approximation for float32 rounding error
    geometry.known_radii = df.loc[df["az_idx"] == 1, "R"].sort_values().round(6).to_list()
    df["R"] = snap_to_ring(df["R"].values, geometry.known_radii, tol=1e-5)

    geometry.known_thetas = df.loc[df["radial_idx"] == 1, "theta"].sort_values().round(3).to_list()
    df["theta"] = snap_to_ring(df["theta"].values, geometry.known_thetas, tol=1e-2)

    # Replace values where density is 0
    mask = df["density"] == 0.0
    df.loc[mask, "density"] = DEFAULT_DENSITY
    df.loc[mask, "velocity"] = DEFAULT_VELOCITY
    df.loc[mask, "pressure"] = DEFAULT_PRESSURE

    vt = np.cos(np.deg2rad(df["theta"])) * df["vel_y"] - np.sin(np.deg2rad(df["theta"])) * df["vel_z"]

    df["swirl"] = np.degrees(np.arctan2(vt, df.vel_x))

    with pd.option_context("display.max_rows", None, "display.max_columns", None, "display.width", 1000):
        print(df, file=open("df.csv", "w"))

    return df


def plot_aip(df: pd.DataFrame, output_dir: Path, properties: List[str], axis: np.ndarray) -> None:
    """
    Generate contour plots for the specified properties using world Y/Z coordinates.

    View convention: looking into the AIP from the front of the aircraft (facing aft).
    Aircraft axes: X+ aft, Y+ starboard, Z+ up.
    The x-axis of the plot is inverted (Y decreasing left-to-right) so that the
    view matches an observer standing in front of the aircraft looking aft —
    the pilot's left (port) side is on the right of the plot.

    A small inset in the upper-right corner shows the plane normal vector components (u,v,w).
    Point labels show absolute X,Y,Z coordinates.
    The fuselage-side arrow adapts based on whether the engine centre is port or
    starboard of the aircraft symmetry plane.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with columns 'Y', 'Z', and one column per entry in ``properties``.
    output_dir : Path
        Directory where PDF plots are saved.
    properties : List[str]
        Property column names to plot.
    axis : np.ndarray
        Unitary vector representing the plane normal (shape: (3,)).
    """
    df = df.copy()
    theta_min = df["theta"].min()
    ghost = df[np.isclose(df["theta"], theta_min)].copy()
    ghost["theta"] = 360.0
    df = pd.concat([df, ghost], ignore_index=True)

    # Probe-ring centre in world coordinates (used for relative labels and fuselage side)
    center_y = float(df["Y"].mean())
    center_z = float(df["Z"].mean())

    # Determine fuselage-side text after x-axis inversion.
    # ax.invert_xaxis() makes high-Y appear on the LEFT of the plot.
    # The fuselage / symmetry plane is at Y ≈ 0.
    #   Port engine  (cy < 0): fuselage (Y > cy, closer to 0) → LEFT  after inversion
    #   Starboard engine (cy > 0): fuselage (Y < cy, closer to 0) → RIGHT after inversion
    if center_y < 0:
        fuselage_label = "← fuselage"
    elif center_y > 0:
        fuselage_label = "fuselage →"
    else:
        fuselage_label = "→ fuselage ←"

    for prop in properties:
        if prop not in df.columns:
            logger.warning(f"Property '{prop}' not found in DataFrame, skipping.")
            continue

        # Use world Y and Z directly — no plane_u/plane_v conversion needed here.
        horiz = df["Y"]  # aircraft Y [m]; axis will be inverted below
        vert = df["Z"]  # aircraft Z [m], + = up
        p = df[prop]

        tolerance: float = 1e-8
        inner_radius = df["R"].min()
        outer_radius = df["R"].max()
        pmin = p.min()
        pmax = p.max()

        outer_arc_df = df[np.isclose(df["R"], outer_radius, atol=tolerance)].sort_values(by="theta", ascending=True)
        inner_arc_df = df[np.isclose(df["R"], inner_radius, atol=tolerance)].sort_values(by="theta", ascending=False)
        boundary_df = pd.concat([outer_arc_df, inner_arc_df], ignore_index=True)
        vertices = boundary_df[["Y", "Z"]].to_numpy()
        path = mpath.Path(vertices)

        fig, ax = plt.subplots(figsize=(8, 8))

        before = set(ax.get_children())

        cmap = "plasma"
        norm = None
        vmin = pmin
        vmax = pmax
        vcenter = (pmax + pmin) / 2
        levels = DEFAULT_PLOT_SMOOTH_LEVEL
        extend = "neither"
        antialiased = False
        if prop.lower() == "swirl":
            cmap = "seismic"
            antialiased = True
            vmax = DEFAULT_MAX_SWIRL  # np.max((abs(pmin), abs(pmax)))
            vmin = DEFAULT_MIN_SWIRL  # -np.max((abs(pmin), abs(pmax)))
            vcenter = 0
            levels = np.linspace(vmin, vmax, DEFAULT_PLOT_SWIRL_LEVEL)
            cmap = colormaps[cmap].copy()
            if pmin < vmin:
                extend = "min"
            if pmax > vmax:
                extend = "max"
            if pmin < vmin and pmax > vmax:
                extend = "both"
            # cmap.set_under("dark blue")  # color for values < vmin
            # cmap.set_over("dark red")  # color for values > vmax
        norm = mcolors.TwoSlopeNorm(vmin=vmin, vcenter=vcenter, vmax=vmax)
        contour = ax.tricontourf(horiz, vert, p, levels=levels, cmap=cmap, norm=norm, antialiased=antialiased, extend=extend)
        plt.colorbar(contour, ax=ax, label=LABEL_MAPPING.get(prop, prop), extend="both")

        contour.set_edgecolor("face")

        patch = mpatches.PathPatch(path, facecolor="none", edgecolor="none")
        # width = outer_radius - inner_radius
        # patch = mpatches.Annulus((center_y, center_z), r=outer_radius, width=width, facecolor="none", edgecolor="none")
        ax.add_patch(patch)

        after = set(ax.get_children())

        for artist in after - before:
            if hasattr(artist, "set_clip_path"):
                artist.set_clip_path(patch)

        # Invert x-axis: Y+ starboard appears on the LEFT (pilot's eye view from front)
        ax.invert_xaxis()

        # Point labels — coordinates relative to probe-ring centre for easy reading
        for _, row in df.iterrows():
            px = row["X"]
            py = row["Y"]
            pz = row["Z"]
            vx = row["vel_x"]
            vy = row["vel_y"]
            vz = row["vel_z"]
            theta = row["theta"]
            # ax.text(row["Y"], row["Z"], f"x={px:+.2f}\ny={py:+.2f}\nz={pz:+.2f}", fontsize=4, ha="center", va="center", alpha=0.7)
            # ax.text(row["Y"], row["Z"], f"vx={vx:+.2f}\nvy={vy:+.2f}\nvz={vz:+.2f}\nvt={vt:+.2f}", fontsize=4, ha="center", va="center", alpha=0.7)
            if prop.lower() == "swirl":
                ax.quiver(row["Y"], row["Z"], vy, vz, scale_units="dots", scale=0.7, width=0.003, color="cyan")

        ax.set_title(f"{prop.upper()}", y=1.05, fontsize=12)  # \n(looking into inlet from front — facing aft)")
        ax.set_xlabel(f"Y  [m]   ({fuselage_label})")
        ax.set_ylabel("Z  [m]")  # ↑
        ax.set_aspect("equal")  # Equal only works for AIP aligned with x, y, or z axis.

        # Display unitary vector components (u,v,w)
        u, v, w = axis
        xlim_min, xlim_max = ax.get_xlim()
        ylim_min, ylim_max = ax.get_ylim()
        x = (xlim_max - xlim_min) * 0.9 + xlim_min
        y = (ylim_max - ylim_min) * 0.98 + ylim_min

        ax.text(x, y, f"plane normal\n({u:.2f}, {v:.2f}, {w:.2f})", ha="center", va="center", fontsize=6, color="black")

        plt.tight_layout()
        fig.savefig(str(output_dir / f"{prop}.pdf"), bbox_inches="tight")
        plt.close(fig)

        logger.info(f"Saved plot for {prop} to {output_dir / f'{prop}.pdf'}")


def run_analysis(working_folder: Path, output_dir: Path | None = None) -> Dict[str, Dict[str, pd.DataFrame | DistortionMetrics]]:
    """
    Main analysis function that processes all probes_* folders with distortion analysis.

    Parameters
    ----------
    working_folder : Path
        Path to the working directory.
    output_dir : Path | None
        Output directory for plots and metrics. Defaults to 'output_probes_dir' in working_folder.

    Returns
    -------
    Dict[str, Dict[str, pd.DataFrame | DistortionMetrics]]
        Dictionary mapping folder names to dicts with 'df' and 'metrics' keys.
    """
    # Resolve output directory
    if output_dir is None:
        output_dir = working_folder / OUTPUT_PROBES_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    # Load shared geometry data
    rake_points_path = working_folder / PROBES_RAKE_POINTS_FILENAME

    try:
        geometry = read_rake_points_file(rake_points_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Failed to read geometry file: {e}", exc_info=True)
        raise

    # Compute center
    try:
        geometry.center, geometry.axis = compute_center(geometry.points_df)
    except ValueError as e:
        logger.error(f"Failed to compute center: {e}", exc_info=True)
        raise

    # Find and process each probes_* folder
    probes_folders = find_probes_folders(working_folder)

    for folder in probes_folders:
        try:
            # Create case-specific output subfolder (remove PROBES_FOLDER_PREFIX)
            case_name = folder.name[len(PROBES_FOLDER_PREFIX) :] if folder.name.startswith(PROBES_FOLDER_PREFIX) else folder.name
            case_output_dir = output_dir / case_name
            case_output_dir.mkdir(parents=True, exist_ok=True)

            df = process_probes_folder(folder, geometry)
            plot_aip(df, case_output_dir, ["density", "pressure", "velocity", "swirl"], geometry.axis)

            # New distortion analysis pipeline
            interpolators, p_avg = build_interpolators(df, geometry)
            sector_results, interpolated_df = compute_sector_sweep_fast(interpolators, geometry.known_radii, p_avg)
            ring_avg, ring_min = compute_ring_averages(df, geometry)
            metrics = compute_distortion_metrics(sector_results, ring_avg, ring_min, df["pressure"].mean(), df["density"].mean(), df["velocity"].mean())

            plot_sector_contour(grid_df=interpolated_df, output_dir=case_output_dir, geometry=geometry)
            plot_dc60(metrics, case_output_dir)

            # Log key distortion metrics
            logger.info(
                f"Folder {folder.name}: IDC={metrics.IDC:.4f}, IDR={metrics.IDR:.4f}, " f"max(DC60_min)={max(metrics.dc60_min):.4f}, max(DC60_avg)={max(metrics.dc60_avg):.4f}"
            )

            results[folder.name] = {"df": df, "metrics": metrics}
        except Exception as e:
            logger.error(f"Error processing folder '{folder.name}': {e}", exc_info=True)
            logger.warning(f"Skipping folder: {folder.name}", exc_info=True)
            continue

    logger.info(f"Analysis complete. Processed {len(results)}/{len(probes_folders)} folders.")

    # Write metrics summary to file
    write_metrics_summary(results, output_dir)

    return results


def write_metrics_summary(results: Dict[str, Dict[str, pd.DataFrame | DistortionMetrics]], output_dir: Path) -> None:
    """
    Write metrics summary to a file.

    Parameters
    ----------
    results : Dict[str, Dict[str, pd.DataFrame | DistortionMetrics]]
        Dictionary mapping folder names to dicts with 'df' and 'metrics' keys.
    output_dir : Path
        Output directory for the metrics file.
    """
    metrics_file = output_dir / "metrics_summary.txt"
    with open(metrics_file, "w", encoding="utf-8") as f:
        f.write("case dc60_min dc60_avg dc60_avg_aip dc60_mfw_aip IDC IDR P_avg_probes P_avg_aip P_avg_mfw\n")
        for case, data in results.items():
            metrics = data["metrics"]
            f.write(
                f"{case} "
                f"{max(metrics.dc60_min):.6f} "
                f"{max(metrics.dc60_avg):.6f} "
                f"{max(metrics.dc60_avg_aip):.6f} "
                f"{max(metrics.dc60_mfw_aip):.6f} "
                f"{metrics.IDC:.6f} "
                f"{metrics.IDR:.6f} "
                f"{metrics.P_avg_probes:.6f} "
                f"{metrics.P_avg_aip:.6f} "
                f"{metrics.P_avg_mfw:.6f}\n"
            )
    logger.info(f"Metrics written to {metrics_file}")


# ============================================================================
# ENTRY POINT
# ============================================================================


def main() -> None:
    """Main entry point for the script."""
    args = parse_arguments()

    # Override log level if verbose flag is set
    if args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = LOG_LEVEL

    logger_instance = setup_logging(level=log_level)

    logger.info("=" * 60)
    logger.info("Starting Fluent Probe Data Processing")
    logger.info(f"Working folder: {args.working_folder}")
    logger.info("=" * 60)

    try:
        # Resolve output directory
        output_dir = args.output if args.output else args.working_folder / OUTPUT_PROBES_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        results = run_analysis(args.working_folder, output_dir)

        logger.info("All tasks completed successfully.")

    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
