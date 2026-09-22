"""
Generates the D-Flow FM external forcing file (.ext).

Format: New-style v3.00 external forcing file with [Boundary] and [Spatial] blocks.
Based on the reference f34_bnd.ext from the installed Delft3D examples.
"""
import os
import logging
from typing import List

logger = logging.getLogger(__name__)


class Delft3DExtGenerator:
    """Generates new-style external forcing files for D-Flow FM."""

    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.output_dir = os.path.join(workspace_path, "boundary")
        os.makedirs(self.output_dir, exist_ok=True)
        self.boundaries: List[dict] = []

    def add_boundary(
        self,
        quantity: str,
        location_file: str,
        forcing_file: str
    ) -> None:
        """
        Registers a boundary for inclusion in the ext file.

        Args:
            quantity: Boundary quantity type ('waterlevelbnd', 'dischargebnd', etc.)
            location_file: Relative path to .pli file
            forcing_file: Relative path to .bc file
        """
        self.boundaries.append({
            "quantity": quantity,
            "locationFile": location_file,
            "forcingFile": forcing_file
        })

    def generate(self, filename: str = "scenario_bnd.ext") -> str:
        """
        Writes the external forcing file.

        Returns:
            Absolute path to the generated .ext file
        """
        ext_path = os.path.join(self.output_dir, filename)

        with open(ext_path, "w") as f:
            f.write("[General]\n")
            f.write("fileVersion = 3.00\n")
            f.write("fileType    = extForce\n")
            f.write("\n")

            for bnd in self.boundaries:
                f.write("[Boundary]\n")
                f.write(f"quantity     = {bnd['quantity']}\n")
                f.write(f"locationFile = {bnd['locationFile']}\n")
                f.write(f"forcingFile  = {bnd['forcingFile']}\n")
                f.write("\n")

        logger.info(f"Generated ext file: {ext_path} with {len(self.boundaries)} boundaries")
        return ext_path
