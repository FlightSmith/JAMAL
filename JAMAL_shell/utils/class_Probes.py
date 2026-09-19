#!/bin/env python3
# -*- coding: utf-8 -*-

# ------------------------------------------------------------------------------
# Name     :      Class rakePoints
# Purpose  :      Generate the raked points and the plots to get the flow
#                 distortion.
#
# Author   :      Flight Sciences
#
# Created  :      12/12/2024
# Copyright:
# Licence  :      <your licence>
#
# Input    :
#
#
# Modifications:
#
#     Ricardo Galdino (09/12/2024)
#     Implementing the methods to class rakedPoints
#
#     Alexandre Antunes (12/12/2024)
#     Coupling the codes...
#
#     Schneider (08/04/2026)
#     Refactor to run as standalone
#
# ------------------------------------------------------------------------------

# Bult-in module
import math
import os
import sys

import numpy as np

# Logging
import logging

import argparse

logger = logging.getLogger(__name__)

# Default values for parameters
DEFAULT_RADIUS = 1
DEFAULT_NUM_POINTS = 18
DEFAULT_NUM_RADII = 6
DEFAULT_AIP_X = 0.0
DEFAULT_AIP_Y = 0.0
DEFAULT_AIP_Z = 0.0
DEFAULT_VEC_X = 1.0
DEFAULT_VEC_Y = 0.0
DEFAULT_VEC_Z = 0.0
DEFAULT_INNER_RADIUS = 0.0
DEFAULT_BC = "Full"
DEFAULT_CODE = "Fluent"
DEFAULT_FILEPATH = "probes"
DEFAULT_ITER = 0
DEFAULT_INCLUDE_OUTER_RADIUS = False
DEFAULT_TRIM_INNER_PCT = 0.0
DEFAULT_TRIM_OUTER_PCT = 0.0


# ------------------------------------------------------------------------------
class Probes:

    def __init__(
        self,
        outer_radius,
        radius=DEFAULT_RADIUS,
        num_points=DEFAULT_NUM_POINTS,
        num_radii=DEFAULT_NUM_RADII,
        aip_x=DEFAULT_AIP_X,
        aip_y=DEFAULT_AIP_Y,
        aip_z=DEFAULT_AIP_Z,
        inner_radius=DEFAULT_INNER_RADIUS,
        bc=DEFAULT_BC,
        vec_x=DEFAULT_VEC_X,
        vec_y=DEFAULT_VEC_Y,
        vec_z=DEFAULT_VEC_Z,
        code=DEFAULT_CODE,
        transfer_file=None,
        write_output=None,
        filepath=DEFAULT_FILEPATH,
        airflow=None,
        iter_count=None,
        include_outer_radius=DEFAULT_INCLUDE_OUTER_RADIUS,
        trim_inner_pct=DEFAULT_TRIM_INNER_PCT,
        trim_outer_pct=DEFAULT_TRIM_OUTER_PCT,
    ):
        """
        Initialize the Probes class with parameters for generating probe points.

        Args:
            radius (int): Radius for the circle.
            num_points (int): Number of points to distribute on the circle.
            num_radii (int): Number of radial positions (defines num_radii-1 annular areas).
            aip_x (float): X-coordinate of the Aerodynamic Interface Plane center.
            aip_y (float): Y-coordinate of the Aerodynamic Interface Plane center.
            aip_z (float): Z-coordinate of the Aerodynamic Interface Plane center.
            vec_x (float): X-component of the plane vector (default 1.0).
            vec_y (float): Y-component of the plane vector (default 0.0).
            vec_z (float): Z-component of the plane vector (default 0.0).
            outer_radius (float): The outer radius.
            inner_radius (float): The inner radius (legacy mode, overridden by trim percentages).
            bc (str): Boundary condition ('Full' or 'Halv').
            code (str): Code format for output (default 'Fluent').
            transfer_file (str or None): Path to transfer file, or None to print to console.
            write_output (str or None): Path to write output file, or None to skip.
            filepath (str or None): Relative filepath for Fluent journal output file paths.
            airflow (str or None): Airflow condition string for Fluent journal output.
            iter_count (int or None): Iteration count for Fluent journal output.
            include_outer_radius (bool): If True, include the outer radius in the output list.
            trim_inner_pct (float): Percentage of total circle area to discard from center (0-100).
            trim_outer_pct (float): Percentage of total circle area to discard from outer edge (0-100).
        """
        self.radius = radius
        self.num_points = num_points
        self.num_radii = num_radii
        self.aip_x = aip_x
        self.aip_y = aip_y
        self.aip_z = aip_z
        self.vec_x = vec_x
        self.vec_y = vec_y
        self.vec_z = vec_z
        self.outer_radius = outer_radius
        self.inner_radius = inner_radius
        self.outer_radius_print = outer_radius
        self.inner_radius_print = inner_radius
        self.bc = bc
        self.code = code
        self.transfer_file = transfer_file
        self.write_output = write_output
        self.filepath = filepath
        self.airflow = airflow
        self.iter_count = iter_count
        self.include_outer_radius = include_outer_radius
        self.trim_inner_pct = trim_inner_pct
        self.trim_outer_pct = trim_outer_pct

        # Validate normal vector is not zero
        if math.isclose(self.vec_x, 0.0, abs_tol=1e-12) and math.isclose(self.vec_y, 0.0, abs_tol=1e-12) and math.isclose(self.vec_z, 0.0, abs_tol=1e-12):
            raise ValueError("Normal vector (vec_x, vec_y, vec_z) must not be the zero vector.")

        # Validate trim percentages
        if self.trim_inner_pct < 0 or self.trim_outer_pct < 0:
            raise ValueError("Trim percentages must be non-negative.")
        if self.trim_inner_pct + self.trim_outer_pct >= 100.0:
            raise ValueError(
                f"Sum of trim_inner_pct ({self.trim_inner_pct}) and trim_outer_pct ({self.trim_outer_pct}) must be less than 100.0 (currently {self.trim_inner_pct + self.trim_outer_pct})."
            )
        # Force include_outer_radius=True when using percentage-based trimming
        if self.trim_inner_pct > 0.0 or self.trim_outer_pct > 0.0:
            self.include_outer_radius = True
            if include_outer_radius == False:
                logger.info("Percentage-based trimming active: forcing include_outer_radius=True")

        # Check for conflicting modes: legacy inner_radius vs percentage-based trimming
        if (self.trim_inner_pct > 0.0 or self.trim_outer_pct > 0.0) and self.inner_radius > 0.0:
            logger.warning(
                f"Both trim percentages (inner={self.trim_inner_pct}, outer={self.trim_outer_pct}) and legacy inner_radius ({self.inner_radius}) specified. Percentage-based trimming takes precedence."
            )

    # ------------------------------------------------------------------------------
    def _compute_plane_basis(self):
        """
        Compute orthonormal basis vectors u_hat and v_hat in the AIP plane
        from the plane normal vector (vec_x, vec_y, vec_z).

        u_hat is the cos-theta direction and v_hat is the sin-theta direction.

        Returns:
            tuple: (u_hat, v_hat) as numpy arrays of shape (3,)
        """
        n = np.array([self.vec_x, self.vec_y, self.vec_z], dtype=float)
        norm = np.linalg.norm(n)

        if norm < 1e-12:
            raise ValueError(f"Normal vector ({self.vec_x}, {self.vec_y}, {self.vec_z}) has near-zero magnitude.")

        n_hat = n / norm

        # Choose reference vector not parallel to n_hat
        if abs(np.dot(n_hat, np.array([0.0, 0.0, 1.0]))) < 0.9:
            ref = np.array([0.0, 0.0, 1.0])
        else:
            ref = np.array([1.0, 0.0, 0.0])

        # v_hat = sin direction, u_hat = cos direction
        v_hat = np.cross(ref, n_hat)
        v_hat = v_hat / np.linalg.norm(v_hat)

        u_hat = np.cross(n_hat, v_hat)
        u_hat = u_hat / np.linalg.norm(u_hat)

        return u_hat, v_hat

    # ------------------------------------------------------------------------------
    def distribute_circle_points(self, bc, num_points):
        """
        Distributes points uniformly on a circle and returns angular components.
        Note: For Full boundary condition, num_points defines num_points slices
        (first probe equals last due to 2*pi periodicity).

        Args:
            bc (str): Boundary condition ('Full' or 'Halv').
            num_points (int): Number of points to distribute.

        Returns:
            list: A list of tuples (cos_theta, sin_theta).
        """
        angle_components = []

        if bc.lower() == "full":
            angle_increment = 2.0 * math.pi / num_points
            for i in range(num_points):
                cos_theta = math.cos(i * angle_increment)
                sin_theta = math.sin(i * angle_increment)
                angle_components.append((cos_theta, sin_theta))

        elif bc.lower() == "halv":
            angle_increment = math.pi / (num_points - 1)
            for i in range(num_points):
                cos_theta = math.cos(i * angle_increment)
                sin_theta = math.sin(-(i * angle_increment))
                angle_components.append((cos_theta, sin_theta))

        return angle_components

    #
    def _compute_trimmed_radii(self, outer_radius, inner_radius, trim_outer_pct=0, trim_inner_pct=0):

        # Cumulative area percentages from center
        # 0% = center, spinner_area/total = physical inner, 100% = outer

        discarded_area_pct = (inner_radius * inner_radius) / (outer_radius * outer_radius) * 100.0
        usable_pct = 100.0 - discarded_area_pct

        inner_effective_discarded_pct = discarded_area_pct + (trim_inner_pct / 100.0) * usable_pct
        ouer_effective_discarded_pct = 100.0 - (trim_outer_pct / 100.0) * usable_pct

        effective_inner = outer_radius * np.sqrt(inner_effective_discarded_pct / 100.0)
        effective_outer = outer_radius * np.sqrt(ouer_effective_discarded_pct / 100.0)

        return effective_inner, effective_outer

    # ------------------------------------------------------------------------------
    def distribute_radii_equal_annular_areas(self, effective_outer, effective_inner, num_radii, trim_outer_pct, trim_inner_pct, radius=1, include_outer_radius=False):
        """
        Distributes radii points with equal annular areas between outer_radius and inner_radius.

        Note: num_radii defines the number of radial positions (vertices/probes).
        The number of annular areas (rings) is num_radii - 1 when endpoints are included,
        or num_radii when counting intermediate rings.

        Args:
            outer_radius (float): The outer radius boundary.
            inner_radius (float): The inner radius boundary.
            num_radii (int): The number of radii vertices to generate.
            include_outer_radius (bool): If True, include the outer radius in the output list.
                                         If False (default), only include intermediate radii points and inner radius if applicable.
        Returns:
            list: A list of radii with equal annular areas between them.
        """
        effective_inner, effective_outer = self._compute_trimmed_radii(effective_outer, effective_inner, trim_outer_pct, trim_inner_pct)

        self.outer_radius_print = effective_outer
        self.inner_radius_print = effective_inner

        area = np.pi * (effective_outer * effective_outer - effective_inner * effective_inner)

        num_endpoints = (1 if include_outer_radius else 0) + (1 if effective_inner != 0.0 else 0)
        num_intermediate = num_radii - num_endpoints

        area_per_radius = area / (num_intermediate + 1)

        radii_points = []
        if include_outer_radius:
            radii_points.append(effective_outer)

        current_radius = effective_outer
        for i in range(num_intermediate):
            inner_radius_calc = np.sqrt(current_radius * current_radius - area_per_radius / np.pi)
            radii_points.append(inner_radius_calc)
            current_radius = inner_radius_calc
            self.inner_radius_print = inner_radius_calc

        if effective_inner > 0:
            radii_points.append(effective_inner)

        radii_points = [x * radius for x in radii_points]
        self.outer_radius_print = radii_points[0]
        self.inner_radius_print = radii_points[-1]
        return radii_points

    # ------------------------------------------------------------------------------
    def _compute_probe_coordinates(self):
        """
        Compute the coordinates for all probe points.

        Returns:
            list: List of tuples (radial_idx, circum_idx, x, y, z)
        """
        # Compute plane basis vectors
        u_hat, v_hat = self._compute_plane_basis()

        # Generate angular components and radii
        self.circle_points = self.distribute_circle_points(self.bc, self.num_points)

        self.radii_points = self.distribute_radii_equal_annular_areas(
            self.outer_radius, self.inner_radius, self.num_radii, self.trim_outer_pct, self.trim_inner_pct, self.radius, self.include_outer_radius
        )

        center = np.array([self.aip_x, self.aip_y, self.aip_z])

        probe_coords = []
        radial_idx = 0
        for radius in self.radii_points:
            radial_idx += 1
            circum_idx = 0
            for cos_theta, sin_theta in self.circle_points:
                circum_idx += 1
                point = center + radius * (cos_theta * u_hat + sin_theta * v_hat)
                probe_coords.append((radial_idx, circum_idx, point[0], point[1], point[2]))

        return probe_coords

    # ------------------------------------------------------------------------------
    def _write_transfer_data(self, probe_coords, transfer_file_handle):
        """
        Write transfer data to the specified file handle or stdout.

        Args:
            probe_coords (list): List of (radial_idx, circum_idx, probe_name, x, y, z) tuples
            transfer_file_handle (file or None): File handle to write to, or None for stdout
        """
        # Writing the number of radial and circumferential probes
        # Note: num_points = num azimuthal slices for Full (first=last)
        if transfer_file_handle:
            transfer_file_handle.write("%s %s \n" % (len(self.circle_points), len(self.radii_points)))
        else:
            print("%s %s" % (len(self.circle_points), len(self.radii_points)))

        # Here I am storing the external and internal radius
        # for the interpolation process for the Post-Processing.
        dext = self.outer_radius_print
        dint = self.inner_radius_print
        if transfer_file_handle:
            transfer_file_handle.write("%9.6f %9.6f \n" % (dext, dint))
        else:
            print("%9.6f %9.6f" % (dext, dint))

        # Writing the coordinate data
        for radial_idx, circum_idx, x, y, z in probe_coords:
            if transfer_file_handle:
                transfer_file_handle.write("%s %s %9.6f %9.6f %9.6f \n" % (radial_idx, circum_idx, x, y, z))
            else:
                print("%s %s %9.6f %9.6f %9.6f" % (radial_idx, circum_idx, x, y, z))

    def _generate_point_surface_commands(self, probe_name, x=0, y=0, z=0, delete=False):
        """
        Generate the extended Fluent TUI commands for a probe point.

        Args:
            probe_name (str): Name of the probe
            x (float): X coordinate
            y (float): Y coordinate
            z (float): Z coordinate
            delete (boolean): delete point surface instead of create

        Returns:
            list: List of Fluent command strings
        """
        if not delete:
            commands = [f"/surface/point-surface {probe_name} {x:.6f} {y:.6f} {z:.6f}"]
        else:
            commands = [f"/surface/delete-surface {probe_name}"]
        return commands

    def _generate_report_commands(self, probe_list=[], use_filepaths=False, include_velocity_components=True, delete=False):
        """
        Generate the extended Fluent TUI commands for a probe point.

        Args:
            probe_name (str): Name of the probe
            x (float): X coordinate
            y (float): Y coordinate
            z (float): Z coordinate
            use_filepaths (boolean): Write properties file on specific folder
            include_velocity_components (boolean): Gather velocity components for each probe

        Returns:
            list: List of Fluent command strings
        """
        prefix = f"{self.filepath}_{self.airflow}/" if use_filepaths else ""
        probe_joined = " ".join(probe_list)
        if not delete:
            commands = [
                f"/solve/report-definitions/add PT surface-areaavg surface-names ({probe_joined}) per-surface? yes field total-pressure q",
                f"/solve/report-files/add PT report-defs (PT) print? no file-name {prefix}total_pressure q",
                f"/solve/report-definitions/add VM surface-areaavg surface-names ({probe_joined}) per-surface? yes field velocity-magnitude q",
                f"/solve/report-files/add VM report-defs (VM) print? no file-name {prefix}velocity-magnitude q",
                f"/solve/report-definitions/add D surface-areaavg surface-names ({probe_joined}) per-surface? yes field density q",
                f"/solve/report-files/add D report-defs (D) print? no file-name {prefix}density q",
            ]
            if include_velocity_components:
                commands.extend(
                    [
                        f"/solve/report-definitions/add VX surface-areaavg surface-names ({probe_joined}) per-surface? yes field x-velocity  q",
                        f"/solve/report-files/add VX report-defs (VX) print? no file-name {prefix}vel_x q",
                        f"/solve/report-definitions/add VY surface-areaavg surface-names ({probe_joined}) per-surface? yes field y-velocity  q",
                        f"/solve/report-files/add VY report-defs (VY) print? no file-name {prefix}vel_y q",
                        f"/solve/report-definitions/add VZ surface-areaavg surface-names ({probe_joined}) per-surface? yes field z-velocity  q",
                        f"/solve/report-files/add VZ report-defs (VZ) print? no file-name {prefix}vel_z q",
                    ]
                )
        else:
            commands = [
                f"/solve/report-files/delete PT",
                f"/solve/report-definitions/delete PT",
                f"/solve/report-files/delete VM",
                f"/solve/report-definitions/delete VM",
                f"/solve/report-files/delete D",
                f"/solve/report-definitions/delete D",
            ]
            if include_velocity_components:
                commands.extend(
                    [
                        f"/solve/report-files/delete VX",
                        f"/solve/report-definitions/delete VX",
                        f"/solve/report-files/delete VY",
                        f"/solve/report-definitions/delete VY",
                        f"/solve/report-files/delete VZ",
                        f"/solve/report-definitions/delete VZ",
                    ]
                )
        return commands

    def _generate_delete_report_commands(self, include_velocity_components=True):
        """
        Generate the extended Fluent TUI commands for a probe point (16 lines).

        Args:
            probe_name (str): Name of the probe
            x (float): X coordinate
            y (float): Y coordinate
            z (float): Z coordinate
            include_velocity_components (boolean): Gather velocity components for each probe

        Returns:
            list: List of Fluent command strings
        """
        # First 7 lines are the same as basic, but with filepath in file-name paths
        commands = [
            f"/solve/report-files/delete PT",
            f"/solve/report-definitions/delete PT",
            f"/solve/report-files/delete VM",
            f"/solve/report-definitions/delete VM",
            f"/solve/report-files/delete D",
            f"/solve/report-definitions/delete D",
        ]
        if include_velocity_components:
            commands.extend(
                [
                    f"/solve/report-files/delete VX",
                    f"/solve/report-definitions/delete VX",
                    f"/solve/report-files/delete VY",
                    f"/solve/report-definitions/delete VY",
                    f"/solve/report-files/delete VZ",
                    f"/solve/report-definitions/delete VZ",
                ]
            )
        return commands

    # ------------------------------------------------------------------------------
    def _generate_fluent_journal_delete_points(self, probe_name, x, y, z, include_velocity_components=True):
        """
        Generate the extended Fluent TUI commands for a probe point (16 lines).

        Args:
            probe_name (str): Name of the probe
            x (float): X coordinate
            y (float): Y coordinate
            z (float): Z coordinate
            include_velocity_components (boolean): Gather velocity components for each probe

        Returns:
            list: List of Fluent command strings
        """
        # First 7 lines are the same as basic, but with filepath in file-name paths
        commands = [
            f"/solve/report-files/delete PT_{probe_name}",
            f"/solve/report-definitions/delete PT_{probe_name}",
            f"/solve/report-files/delete VM_{probe_name}",
            f"/solve/report-definitions/delete VM_{probe_name}",
            f"/solve/report-files/delete D_{probe_name}",
            f"/solve/report-definitions/delete D_{probe_name}",
        ]
        if include_velocity_components:
            commands.extend(
                [
                    f"/solve/report-files/delete VX_{probe_name}",
                    f"/solve/report-definitions/delete VX_{probe_name}",
                    f"/solve/report-files/delete VY_{probe_name}",
                    f"/solve/report-definitions/delete VY_{probe_name}",
                    f"/solve/report-files/delete VZ_{probe_name}",
                    f"/solve/report-definitions/delete VZ_{probe_name}",
                    f"/surface/delete-surface {probe_name}",
                ]
            )
        return commands

    # ------------------------------------------------------------------------------
    def _write_output(self, probe_coords, output_file):
        """
        Write commands for all probes to the specified output.

        Args:
            probe_coords (list): List of (radial_idx, circum_idx, probe_name, x, y, z) tuples
            output_file (file or None): File handle to write to, or None for stdout
        """
        # Determine if we should use extended (journal) or basic commands
        use_filepaths = self.airflow is not None
        lines = []
        probes_list = []

        if use_filepaths:
            lines.append(f"! mkdir -p {self.filepath}_{self.airflow}")

        for radial_idx, circum_idx, x, y, z in probe_coords:
            probe_name = f"P_{radial_idx}_{circum_idx}"
            lines.extend(self._generate_point_surface_commands(probe_name, x, y, z))
            probes_list.append(probe_name)

        lines.extend(self._generate_report_commands(probes_list, use_filepaths=use_filepaths))

        lines.append(f"solve  iterate {self.iter_count}")

        lines.extend(self._generate_report_commands(probes_list, use_filepaths=use_filepaths, delete=True))

        for probe_name in probes_list:
            lines.extend(self._generate_point_surface_commands(probe_name, delete=True))
        for line in lines:
            if output_file:
                output_file.write(line + "\n")
            else:
                print(line)

    # ------------------------------------------------------------------------------
    def generate_probes(self):
        """
        This method generates and writes the probe data.
        """
        # Logging.
        logger.info("Generating the Probes.")

        # Compute all probe coordinates
        probe_coords = self._compute_probe_coordinates()

        # Handle transfer file output
        transfer_file_path = self.transfer_file
        transfer_file_handle = open(transfer_file_path, "w") if transfer_file_path else None

        # Write transfer data
        self._write_transfer_data(probe_coords, transfer_file_handle)

        # Handle Fluent output if requested
        if self.code.lower() == "fluent":
            output_file_path = self.write_output
            output_file = open(output_file_path, "w") if output_file_path else None
            self._write_output(probe_coords, output_file)
            if output_file:
                output_file.close()

        # Close transfer file if opened
        if transfer_file_handle:
            transfer_file_handle.close()


def main():
    parser = argparse.ArgumentParser(description="Generate probe points for CFD simulations.")
    parser.add_argument("-r", "--radius", type=int, default=DEFAULT_RADIUS, required=False, help="Radius for the circle (default %(default)s).")
    parser.add_argument(
        "-p",
        "--num-points",
        type=int,
        default=DEFAULT_NUM_POINTS,
        required=False,
        help="Number of points to distribute on the circle (default %(default)s). Note: For Full BC, this equals the number of azimuthal slices.",
    )
    parser.add_argument(
        "-N",
        "--num-radii",
        type=int,
        default=DEFAULT_NUM_RADII,
        required=False,
        help="Number of radial positions (vertices/probes). The number of annular areas is num-radii - 1 when endpoints included (default %(default)s).",
    )
    parser.add_argument("-x", "--aip-x", type=float, default=DEFAULT_AIP_X, required=False, help="X-coordinate of the Aerodynamic Interface Plane center (default %(default)s).")
    parser.add_argument("-y", "--aip-y", type=float, default=DEFAULT_AIP_Y, required=False, help="Y-coordinate of the Aerodynamic Interface Plane center (default %(default)s).")
    parser.add_argument("-z", "--aip-z", type=float, default=DEFAULT_AIP_Z, required=False, help="Z-coordinate of the Aerodynamic Interface Plane center (default %(default)s).")
    parser.add_argument("-u", "--vec-x", type=float, default=DEFAULT_VEC_X, help="X-component of the plane vector (default %(default)s).")
    parser.add_argument("-v", "--vec-y", type=float, default=DEFAULT_VEC_Y, help="Y-component of the plane vector (default %(default)s).")
    parser.add_argument("-w", "--vec-z", type=float, default=DEFAULT_VEC_Z, help="Z-component of the plane vector (default %(default)s).")
    ###
    parser.add_argument("-o", "--outer-radius", type=float, required=True, help="The outer radius.")
    parser.add_argument(
        "-i",
        "--inner-radius",
        type=float,
        default=DEFAULT_INNER_RADIUS,
        required=False,
        help="The inner radius (legacy mode, overridden by --trim-inner-pct/--trim-outer-pct) (default %(default)s).",
    )
    parser.add_argument(
        "--trim-inner-pct",
        type=float,
        default=DEFAULT_TRIM_INNER_PCT,
        help="Percentage of total circle area to discard from center (0-100). Overrides inner-radius when >0 (default %(default)s).",
    )
    parser.add_argument(
        "--trim-outer-pct", type=float, default=DEFAULT_TRIM_OUTER_PCT, help="Percentage of total circle area to discard from outer edge (0-100) (default %(default)s)."
    )
    parser.add_argument("-b", "--bc", choices=["Full", "Halv"], default=DEFAULT_BC, required=False, help="Boundary condition (Full or Halv) (default %(default)s).")
    parser.add_argument("-c", "--code", type=str, default="Fluent", help="Code format for output (default Fluent).")
    parser.add_argument("-t", "--transfer-file", type=str, help="Path to transfer file (optional, prints to console if not provided).")
    parser.add_argument("-W", "--write-output", type=str, help="Path to write output file (optional, skips if not provided).")
    parser.add_argument("-f", "--filepath", type=str, default=DEFAULT_FILEPATH, help="Relative filepath for Fluent probes output file.")
    parser.add_argument("-a", "--airflow", type=str, help="Airflow condition string for Fluent probes filename.")
    parser.add_argument("--iter", type=int, default=DEFAULT_ITER, help="Iteration count for Fluent journal output.")
    parser.add_argument(
        "-O", "--include-outer-radius", action="store_true", default=DEFAULT_INCLUDE_OUTER_RADIUS, help="Include the outer radius in the output list (default %(default)s)."
    )

    args = parser.parse_args()

    if args.bc != "Full":
        logger.critical("Post does not handle half model")
        sys.exit(-1)

    # Instantiate the class
    probes = Probes(
        outer_radius=args.outer_radius,
        radius=args.radius,
        num_points=args.num_points,
        num_radii=args.num_radii,
        aip_x=args.aip_x,
        aip_y=args.aip_y,
        aip_z=args.aip_z,
        vec_x=args.vec_x,
        vec_y=args.vec_y,
        vec_z=args.vec_z,
        inner_radius=args.inner_radius,
        bc=args.bc,
        code=args.code,
        transfer_file=args.transfer_file,
        write_output=args.write_output,
        filepath=args.filepath,
        airflow=args.airflow,
        iter_count=args.iter,
        include_outer_radius=args.include_outer_radius,
        trim_inner_pct=args.trim_inner_pct,
        trim_outer_pct=args.trim_outer_pct,
    )

    # Generate the probes
    probes.generate_probes()


if __name__ == "__main__":
    main()
