"""
Generates D-Flow FM structure .ini files for dambreak, weir, and dam structures.

Based on the installed D-Flow FM 1.2.184 source code analysis:
- Structure type 'dambreak' is a native D-Flow FM structure
- Three breach growth algorithms are supported:
  Algorithm 1: Van der Knaap
  Algorithm 2: Verheij-van der Knaap (physics-based)
  Algorithm 3: Timeseries (user-provided breach width vs time)
"""
import os
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class Delft3DStructureGenerator:
    """Generates D-Flow FM structure .ini files."""

    def __init__(self, workspace_path: str):
        self.output_dir = os.path.join(workspace_path, "config")
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_dambreak_structure(
        self,
        structure_id: str,
        polyline_coords: List[Tuple[float, float]],
        start_location: Tuple[float, float],
        crest_level_ini: float,
        breach_width_ini: float = 10.0,
        crest_level_min: float = 0.0,
        time_to_breach_max_depth: float = 3600.0,
        f1: float = 1.3,
        f2: float = 0.04,
        u_crit: float = 0.2,
        upstream_location: Optional[Tuple[float, float]] = None,
        downstream_location: Optional[Tuple[float, float]] = None,
        algorithm: int = 2,
        breach_timeseries: Optional[List[Tuple[float, float]]] = None,
        t0: float = 0.0
    ) -> Tuple[str, str]:
        """
        Generates a dambreak structure .ini file and its polyline .pli file.

        Args:
            structure_id: Unique identifier for the structure
            polyline_coords: List of (x, y) defining the dam polyline geometry
            start_location: (x, y) of the breach start point
            crest_level_ini: Initial crest level of the dam (m above datum)
            breach_width_ini: Initial breach width at failure start (m)
            crest_level_min: Minimum crest level the breach can erode to (m)
            time_to_breach_max_depth: Time for breach to reach max depth (s)
            f1, f2: Verheij-van der Knaap breach growth coefficients
            u_crit: Critical flow velocity for breach growth (m/s)
            upstream_location: Optional (x, y) for upstream water level sensing
            downstream_location: Optional (x, y) for downstream water level sensing
            algorithm: Breach growth algorithm (1=VdKnaap, 2=Verheij-VdKnaap, 3=Timeseries)
            breach_timeseries: For algorithm=3, list of (time_s, breach_width_m)

        Returns:
            Tuple of (structure_ini_path, polyline_pli_path) as absolute paths
        """
        # 1. Write the polyline (.pli) for the dam geometry
        pli_filename = f"{structure_id}.pli"
        pli_path = os.path.join(self.output_dir, pli_filename)

        with open(pli_path, "w") as f:
            f.write(f"{structure_id}\n")
            f.write(f"{len(polyline_coords)} 2\n")
            for i, (x, y) in enumerate(polyline_coords):
                f.write(f"{x:.6f} {y:.6f} {structure_id}_{i+1:04d}\n")

        # Also copy pli to workspace root if workspace_path is parent
        workspace_root = os.path.dirname(self.output_dir)
        root_pli_path = os.path.join(workspace_root, pli_filename)
        with open(root_pli_path, "w") as f_root:
            f_root.write(f"{structure_id}\n")
            f_root.write(f"{len(polyline_coords)} 2\n")
            for i, (x, y) in enumerate(polyline_coords):
                f_root.write(f"{x:.6f} {y:.6f} {structure_id}_{i+1:04d}\n")

        # 2. Write the structure definition (.ini)
        ini_filename = f"structures.ini"
        ini_path = os.path.join(self.output_dir, ini_filename)

        with open(ini_path, "w") as f:
            f.write("[Structure]\n")
            f.write(f"type                              = dambreak\n")
            f.write(f"id                                = {structure_id}\n")
            f.write(f"polylinefile                      = config/{pli_filename}\n")
            f.write(f"StartLocationX                    = {start_location[0]:.6f}\n")
            f.write(f"StartLocationY                    = {start_location[1]:.6f}\n")
            f.write(f"t0                                = {t0:.1f}\n")
            f.write(f"Algorithm                         = {algorithm}\n")
            f.write(f"CrestLevelIni                     = {crest_level_ini:.3f}\n")

            if algorithm == 2:  # Verheij-van der Knaap
                f.write(f"BreachWidthIni                    = {breach_width_ini:.3f}\n")
                f.write(f"CrestLevelMin                     = {crest_level_min:.3f}\n")
                f.write(f"TimeToBreachToMaximumDepth        = {time_to_breach_max_depth:.1f}\n")
                f.write(f"F1                                = {f1:.4f}\n")
                f.write(f"F2                                = {f2:.4f}\n")
                f.write(f"Ucrit                             = {u_crit:.4f}\n")

                if upstream_location:
                    f.write(f"WaterLevelUpstreamLocationX       = {upstream_location[0]:.6f}\n")
                    f.write(f"WaterLevelUpstreamLocationY       = {upstream_location[1]:.6f}\n")
                if downstream_location:
                    f.write(f"WaterLevelDownstreamLocationX     = {downstream_location[0]:.6f}\n")
                    f.write(f"WaterLevelDownstreamLocationY     = {downstream_location[1]:.6f}\n")

            elif algorithm == 3:  # Timeseries
                if breach_timeseries:
                    ts_filename = f"{structure_id}_breach.tim"
                    ts_path = os.path.join(self.output_dir, ts_filename)
                    workspace_root = os.path.dirname(self.output_dir)
                    root_ts_path = os.path.join(workspace_root, ts_filename)
                    
                    content = ""
                    for t, w in breach_timeseries:
                        content += f"{t:.1f} {w:.3f}\n"

                    with open(ts_path, "w") as ts_f:
                        ts_f.write(content)
                    with open(root_ts_path, "w") as ts_f:
                        ts_f.write(content)

                    f.write(f"dambreakLevelsAndWidths           = {ts_filename}\n")

            f.write("\n")

        logger.info(f"Generated dambreak structure: {ini_path}")
        return ini_path, pli_path

    def generate_thin_dam(
        self,
        dam_id: str,
        polyline_coords: List[Tuple[float, float]],
        crest_level: float
    ) -> str:
        """
        Generates a thin dam polyline file (.pli) for representing
        impermeable barriers in the mesh. Used for blockages.

        Returns:
            Absolute path to the thin dam .pli file
        """
        pli_filename = f"{dam_id}_thd.pli"
        pli_path = os.path.join(self.output_dir, pli_filename)

        with open(pli_path, "w") as f:
            f.write(f"{dam_id}\n")
            f.write(f"{len(polyline_coords)} 2\n")
            for x, y in polyline_coords:
                f.write(f"{x:.6f} {y:.6f}\n")

        logger.info(f"Generated thin dam: {pli_path}")
        return pli_path
