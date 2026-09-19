import os
import re
import logging
from typing import Dict
from app.utils.ref_metadata import RefMetadata

logger = logging.getLogger(__name__)

# Regex to match section headers: =====[NAME]=====
_section_header_re = re.compile(r"^=+\[([A-Z_]+)\]=+$")


def parse_ref_file(filepath: str) -> RefMetadata:
    """
    Parse REF file and extract section sizes.

    Args:
        filepath: Path to the REF file

    Returns:
        RefMetadata object with section names and element counts

    Raises:
        FileNotFoundError: If REF file doesn't exist
        ValueError: If REF format is invalid
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"REF file not found: {filepath}")

    logger.info(f"Parsing REF file: {filepath}")

    sections = {}
    current_section = None

    with open(filepath, "r") as ref_file:
        for line_num, line in enumerate(ref_file, 1):
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Check if line is a section header
            header_match = _section_header_re.match(line)
            if header_match:
                current_section = header_match.group(1)
                logger.debug(f"Found section: {current_section}")
                continue

            # If we're in a section, parse the first data line to get element count
            if current_section and current_section not in sections:
                # First line after section header defines the count
                # Format: "PROP:  1       2       3       4       5"
                parts = re.split(r"\s+", line)

                # First part is the label (e.g., "PROP:"), rest are element indices
                if len(parts) < 2:
                    logger.warning(f"Line {line_num}: Expected at least 2 parts, got {len(parts)}")
                    continue

                # Count elements (skip the label)
                element_count = len(parts) - 1
                sections[current_section] = element_count

                logger.debug(f"Section '{current_section}' has {element_count} elements")

                # Reset current_section to avoid re-processing
                current_section = None

    if not sections:
        raise ValueError(f"No valid sections found in REF file: {filepath}")

    logger.info(f"Parsed {len(sections)} sections from REF file")
    return RefMetadata(sections)


def resolve_ref_filepath(ref_id: str, base_dir: str = ".") -> str:
    """
    Resolve REF file path from ID.

    Args:
        ref_id: REF identifier (e.g., "123" or "001")
        base_dir: Base directory for resolution (default: current directory)

    Returns:
        Full path to REF file

    Raises:
        FileNotFoundError: If REF file doesn't exist
    """
    # Construct path: ./00-SUPPORT/REF-{ID}
    ref_filename = f"REF-{ref_id}"
    ref_filepath = os.path.join(base_dir, "00-SUPPORT", ref_filename)

    if not os.path.exists(ref_filepath):
        raise FileNotFoundError(f"REF file not found: {ref_filepath} (ID: {ref_id})")

    logger.debug(f"Resolved REF ID '{ref_id}' to path: {ref_filepath}")
    return ref_filepath
