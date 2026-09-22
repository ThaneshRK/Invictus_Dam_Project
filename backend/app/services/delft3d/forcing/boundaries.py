"""
Generates D-Flow FM boundary condition files.

File formats match D-Flow FM 1.2.184:
- .pli: Polyline geometry with named nodes
- .bc: Boundary condition forcing (v1.01 format with [General]/[Forcing] blocks)

Based on reference files from the installed Delft3D examples.
"""
import os
import logging
from typing import List, Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)


class Delft3DBoundaryGenerator:
    """Generates real Delft3D-FM boundary geometries (.pli) and forcing data (.bc)."""

    def __init__(self, workspace_path: str):
        self.output_dir = os.path.join(workspace_path, "boundary")
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_boundary_polyline(
        self,
        name: str,
        coordinates: List[Tuple[float, float]],
        filename: Optional[str] = None
    ) -> str:
        """
        Creates a polyline (.pli) file defining a boundary location.

        Format matches D-Flow FM reference:
            <name>
            <num_points> 2
            <x1> <y1> <name>_0001
            <x2> <y2> <name>_0002

        Args:
            name: Boundary identifier
            coordinates: List of (x, y) points defining the boundary line
            filename: Optional override filename

        Returns:
            Absolute path to the generated .pli file
        """
        pli_filename = filename or f"{name}.pli"
        pli_path = os.path.join(self.output_dir, pli_filename)
        root_pli_path = os.path.join(os.path.dirname(self.output_dir), pli_filename)

        content = f"{name}\n{len(coordinates):>5} 2\n"
        for i, (x, y) in enumerate(coordinates):
            content += f"{x:.12E} {y:.12E} {name}_{i+1:04d}\n"

        with open(pli_path, "w") as f:
            f.write(content)

        with open(root_pli_path, "w") as f:
            f.write(content)

        logger.info(f"Generated boundary polyline: {pli_path}")
        return pli_path

    def generate_discharge_bc(
        self,
        name: str,
        time_series: List[Tuple[float, float]],
        node_names: List[str],
        filename: Optional[str] = None
    ) -> str:
        bc_filename = filename or f"{name}.bc"
        bc_path = os.path.join(self.output_dir, bc_filename)
        root_bc_path = os.path.join(os.path.dirname(self.output_dir), bc_filename)

        content = "[General]\nfileVersion           = 1.01\nfileType              = boundConds\n\n"
        for node_name in node_names:
            content += f"[Forcing]\nname                  = {node_name}\nfunction              = timeseries\nTime-interpolation    = linear\nquantity              = time\nunit                  = minutes since 2024-01-01 00:00:00\nquantity              = dischargebnd\nunit                  = m3/s\n"
            for t, q in time_series:
                content += f"{t:.1f} {q:.3f}\n"
            content += "\n"

        with open(bc_path, "w") as f:
            f.write(content)

        with open(root_bc_path, "w") as f:
            f.write(content)

        logger.info(f"Generated discharge BC: {bc_path}")
        return bc_path

    def generate_waterlevel_bc(
        self,
        name: str,
        time_series: List[Tuple[float, float]],
        node_names: List[str],
        filename: Optional[str] = None
    ) -> str:
        bc_filename = filename or f"{name}.bc"
        bc_path = os.path.join(self.output_dir, bc_filename)
        root_bc_path = os.path.join(os.path.dirname(self.output_dir), bc_filename)

        content = "[General]\nfileVersion           = 1.01\nfileType              = boundConds\n\n"
        for node_name in node_names:
            content += f"[Forcing]\nname                  = {node_name}\nfunction              = timeseries\nTime-interpolation    = linear\nquantity              = time\nunit                  = minutes since 2024-01-01 00:00:00\nquantity              = waterlevelbnd\nunit                  = m\n"
            for t, wl in time_series:
                content += f"{t:.1f} {wl:.3f}\n"
            content += "\n"

        with open(bc_path, "w") as f:
            f.write(content)

        with open(root_bc_path, "w") as f:
            f.write(content)

        logger.info(f"Generated water level BC: {bc_path}")
        return bc_path

    @staticmethod
    def generate_dam_break_hydrograph(
        peak_discharge: float,
        time_to_peak_mins: float,
        total_duration_mins: float
    ) -> List[Tuple[float, float]]:
        """
        Synthesizes a triangular hydrograph for a dam break.
        Used when real time-series data is not available.

        Returns:
            List of (time_minutes, discharge_m3s)
        """
        return [
            (0.0, 0.0),
            (time_to_peak_mins, peak_discharge),
            (total_duration_mins, 0.0)
        ]

    @staticmethod
    def generate_constant_discharge(
        discharge: float,
        duration_mins: float,
        ramp_time_mins: float = 5.0
    ) -> List[Tuple[float, float]]:
        """
        Creates a constant discharge with optional linear ramp-up.

        Returns:
            List of (time_minutes, discharge_m3s)
        """
        return [
            (0.0, 0.0),
            (ramp_time_mins, discharge),
            (duration_mins, discharge)
        ]


# Allow Optional import
from typing import Optional
