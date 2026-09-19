from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class RefMetadata:
    """
    Encapsulates metadata extracted from REF file.

    Stores section names and their corresponding element counts.
    """

    def __init__(self, sections: Dict[str, int]):
        """
        Initialize RefMetadata.

        Args:
            sections: Dictionary mapping section names to element counts
                     Example: {"PROPELLER": 5, "FLAP": 4}
        """
        self.sections = sections
        logger.debug(f"RefMetadata initialized with sections: {sections}")

    def get_expected_length(self, section_name: str) -> Optional[int]:
        """
        Get expected length for a section.

        Args:
            section_name: Name of the section (e.g., "PROPELLER")

        Returns:
            Number of elements in the section, or None if section doesn't exist
        """
        length = self.sections.get(section_name)
        if length is None:
            logger.debug(f"Section '{section_name}' not found in REF metadata")
        return length

    def has_section(self, section_name: str) -> bool:
        """Check if a section exists in the REF file."""
        return section_name in self.sections

    def __repr__(self) -> str:
        return f"RefMetadata(sections={self.sections})"
