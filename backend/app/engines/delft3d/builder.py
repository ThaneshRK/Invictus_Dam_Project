"""
Builds complete D-Flow FM simulation workspaces for three scenario types:
  1. DAM_BREAK — native ST_DAMBREAK structure with Verheij-van der Knaap breach
  2. WATER_RELEASE / CONTROLLED_RELEASE — discharge boundary with Q(t) hydrograph
  3. RIVER_BLOCKAGE — elevated terrain blockage + dambreak structure for failure

MDU format matches D-Flow FM 1.2.184 (installed version).
Physical model: 2D depth-averaged shallow water equations (Kmx=0).
"""
import os
import logging
from typing import Dict, Any
from datetime import datetime

from app.services.delft3d.mesh.generator import Delft3DMeshGenerator
from app.services.delft3d.terrain.sampler import Delft3DTerrainSampler
from app.services.delft3d.forcing.boundaries import Delft3DBoundaryGenerator
from app.services.delft3d.forcing.ext_generator import Delft3DExtGenerator
from app.services.delft3d.forcing.structure_generator import Delft3DStructureGenerator

logger = logging.getLogger(__name__)


class Delft3DModelBuilder:
    """Builds the simulation workspace and configuration for D-Flow FM."""

    def __init__(self, workspace_root: str, simulation_id: str, context: Any):
        self.workspace_root = workspace_root
        self.simulation_id = simulation_id
        self.context = context
        self.params = self.context.scenario.parameters or {}
        self.workspace_path = os.path.join(self.workspace_root, f"job_{self.simulation_id}")
        self.metadata = {}
        
        from geoalchemy2.shape import to_shape
        import rasterio
        
        # Determine bounds from study_area or DEM
        self.bounds = [0.0, 0.0, 1000.0, 1000.0]
        dem_path = None
        if self.context.dem:
            dem_path = getattr(self.context.dem, "file_path", None)
            if not dem_path and getattr(self.context.dem, "metadata_", None) and isinstance(self.context.dem.metadata_, dict):
                dem_path = self.context.dem.metadata_.get("file_path")

        if dem_path and os.path.exists(dem_path):
            with rasterio.open(dem_path) as src:
                self.bounds = [src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top]
        elif hasattr(self.context, 'study_area') and self.context.study_area:
            from geoalchemy2.shape import to_shape
            study_geom = to_shape(self.context.study_area)
            b = study_geom.bounds
            self.bounds = [b[0], b[1], b[2], b[3]]

    def prepare_workspace(self) -> None:
        """Creates the necessary directory structure."""
        dirs = ["mesh", "terrain", "boundary", "config", "output", "logs", "metadata"]
        for d in dirs:
            os.makedirs(os.path.join(self.workspace_path, d), exist_ok=True)

    def _get_scenario_type(self) -> str:
        """Extracts the scenario type from context."""
        st = self.context.scenario.scenario_type
        scen_str = st.value if hasattr(st, 'value') else str(st)
        return scen_str.upper().replace("CONTROLLED_RELEASE", "WATER_RELEASE")

    def _get_bounds(self) -> tuple:
        """Gets simulation domain bounds."""
        return tuple(self.bounds)

    def _get_physics_params(self) -> dict:
        """Gets physics parameters from context."""
        return self.params

    def _get_time_params(self) -> dict:
        """Gets time control parameters."""
        return {
            "duration_hours": self.context.scenario.simulation_duration,
            "timestep_seconds": self.context.scenario.timestep
        }

    def _build_mesh(self) -> str:
        """Generates the computational mesh and returns relative path."""
        mg = Delft3DMeshGenerator(os.path.join(self.workspace_path, "mesh"))
        bounds = self._get_bounds()
        resolution = self.params.get("mesh_resolution", 50.0)

        mesh_abs = mg.generate_rectangular_mesh(bounds, resolution=resolution)
        rel_path = os.path.relpath(mesh_abs, self.workspace_path)

        self.metadata["mesh"] = {
            "bounds": list(bounds),
            "resolution": resolution,
            "file": rel_path
        }
        return rel_path

    def _build_terrain(self) -> str:
        """Samples DEM and generates .xyz bathymetry file. Returns relative path or empty string."""
        dem_file_path = None
        if self.context.dem:
            dem_file_path = getattr(self.context.dem, "file_path", None)
            if not dem_file_path and getattr(self.context.dem, "metadata_", None) and isinstance(self.context.dem.metadata_, dict):
                dem_file_path = self.context.dem.metadata_.get("file_path")

        if dem_file_path and os.path.exists(dem_file_path):
            ts = Delft3DTerrainSampler(self.workspace_path)
            bounds = self._get_bounds()
            xyz_path = ts.generate_xyz_bathymetry(dem_file_path, bounds)
            rel_path = os.path.relpath(xyz_path, self.workspace_path)

            self.metadata["terrain"] = {
                "source": dem_file_path,
                "format": "xyz",
                "file": rel_path
            }
            return rel_path

        return ""

    def _build_dam_break(self, mdu_config: dict) -> None:
        """Configures a dam break scenario using native D-Flow FM ST_DAMBREAK structure."""
        params = self._get_physics_params()
        bounds = self._get_bounds()
        xmin, ymin, xmax, ymax = bounds

        from geoalchemy2.shape import to_shape
        dam_geom = to_shape(self.context.dam.geometry)
        dam_x = dam_geom.x
        dam_y_min = dam_geom.y - 100.0
        dam_y_max = dam_geom.y + 100.0

        # Dam polyline (across the domain)
        dam_polyline = [
            (dam_x, dam_y_min),
            (dam_x, dam_y_max)
        ]

        # Breach start point (center of dam)
        breach_x = dam_x
        breach_y = (dam_y_min + dam_y_max) / 2.0

        # Structure generator
        sg = Delft3DStructureGenerator(self.workspace_path)

        crest_level = params.get("breach_elevation", params.get("crest_level", 10.0))
        breach_width = params.get("breach_width", 20.0)
        crest_min = params.get("crest_level_min", 0.0)
        t_breach = params.get("breach_formation_time", 1.0) * 3600  # hours -> seconds
        f1 = params.get("f1", 1.3)
        f2 = params.get("f2", 0.04)
        u_crit = params.get("u_crit", 0.2)

        # Upstream/downstream sensing locations
        upstream_loc = (dam_x - (xmax - xmin) * 0.1, breach_y)
        downstream_loc = (dam_x + (xmax - xmin) * 0.1, breach_y)

        ini_path, pli_path = sg.generate_dambreak_structure(
            structure_id="dam_breach",
            polyline_coords=dam_polyline,
            start_location=(breach_x, breach_y),
            crest_level_ini=crest_level,
            breach_width_ini=breach_width,
            crest_level_min=crest_min,
            time_to_breach_max_depth=t_breach,
            f1=f1,
            f2=f2,
            u_crit=u_crit,
            upstream_location=upstream_loc,
            downstream_location=downstream_loc,
            algorithm=2  # Verheij-van der Knaap
        )

        # Add structure file to MDU
        mdu_config["geometry"]["StructureFile"] = os.path.relpath(ini_path, self.workspace_path)

        # Initial water level upstream of dam
        initial_wl = params.get("initial_water_level", 10.0)
        mdu_config["geometry"]["WaterLevIni"] = initial_wl

        self.metadata["scenario"] = {
            "type": "DAM_BREAK",
            "breach_algorithm": "Verheij-van der Knaap (Algorithm 2)",
            "crest_level_ini": crest_level,
            "breach_width_ini": breach_width,
            "initial_water_level": initial_wl,
            "structure_file": os.path.relpath(ini_path, self.workspace_path)
        }

    def _build_controlled_release(self, mdu_config: dict) -> None:
        """Configures a controlled water release scenario with Q(t) discharge boundary."""
        params = self._get_physics_params()
        bounds = self._get_bounds()
        xmin, ymin, xmax, ymax = bounds

        from geoalchemy2.shape import to_shape
        res_geom = to_shape(self.context.reservoir.geometry)
        release_x = res_geom.bounds[2]  # Max X of reservoir roughly
        release_y_min = res_geom.bounds[1]
        release_y_max = res_geom.bounds[3]

        bnd_coords = [
            (release_x, release_y_min),
            (release_x, release_y_max)
        ]

        bg = Delft3DBoundaryGenerator(self.workspace_path)
        ext = Delft3DExtGenerator(self.workspace_path)

        # Generate boundary polyline
        pli_path = bg.generate_boundary_polyline("release", bnd_coords)
        node_names = [f"release_{i+1:04d}" for i in range(len(bnd_coords))]

        # Build discharge time series
        release_curve = params.get("release_curve")
        if release_curve and isinstance(release_curve, list):
            # User-provided Q(t) time series
            time_series = [(entry.get("time", 0), entry.get("discharge", 0)) for entry in release_curve]
        else:
            # Generate from peak_discharge and release_duration
            peak_q = params.get("peak_discharge", 500.0)
            duration_mins = params.get("release_duration", 2.0) * 60  # hours -> minutes
            initial_q = params.get("initial_discharge", 0.0)

            time_series = Delft3DBoundaryGenerator.generate_constant_discharge(
                peak_q, duration_mins
            )
            if initial_q > 0:
                time_series[0] = (0.0, initial_q)

        bc_path = bg.generate_discharge_bc("release", time_series, node_names)

        # Register in ext file
        pli_rel = os.path.relpath(pli_path, os.path.join(self.workspace_path, "boundary"))
        bc_rel = os.path.relpath(bc_path, os.path.join(self.workspace_path, "boundary"))
        ext.add_boundary("dischargebnd", pli_rel, bc_rel)

        # Downstream open boundary (water level)
        ds_coords = [(xmax, ymin), (xmax, ymax)]
        ds_pli = bg.generate_boundary_polyline("downstream", ds_coords, "downstream.pli")
        ds_nodes = [f"downstream_{i+1:04d}" for i in range(len(ds_coords))]
        ds_wl = params.get("initial_downstream_condition", 0.0)
        duration_mins_total = self._get_time_params().get("duration_hours", 24) * 60
        ds_ts = [(0.0, ds_wl), (duration_mins_total, ds_wl)]
        ds_bc = bg.generate_waterlevel_bc("downstream", ds_ts, ds_nodes, "downstream.bc")
        ds_pli_rel = os.path.relpath(ds_pli, os.path.join(self.workspace_path, "boundary"))
        ds_bc_rel = os.path.relpath(ds_bc, os.path.join(self.workspace_path, "boundary"))
        ext.add_boundary("waterlevelbnd", ds_pli_rel, ds_bc_rel)

        ext_path = ext.generate()
        mdu_config["external forcing"] = {
            "ExtForceFileNew": os.path.relpath(ext_path, self.workspace_path)
        }

        # Initial water level
        mdu_config["geometry"]["WaterLevIni"] = params.get("initial_water_level", 0.0)

        self.metadata["scenario"] = {
            "type": "CONTROLLED_RELEASE",
            "peak_discharge": params.get("peak_discharge", 500.0),
            "time_series_points": len(time_series),
            "has_user_hydrograph": release_curve is not None
        }

    def _build_river_blockage(self, mdu_config: dict) -> None:
        """Configures a river blockage / landslide scenario.

        The blockage is represented as:
        1. Elevated bed level in the blockage zone (via modified xyz bathymetry)
        2. A dambreak structure at the blockage location for the failure
        3. Upstream inflow boundary representing the river discharge
        """
        params = self._get_physics_params()
        bounds = self._get_bounds()
        xmin, ymin, xmax, ymax = bounds

        from geoalchemy2.shape import to_shape
        river_geom = to_shape(self.context.river.geometry)
        
        # Use river bounds or representative point for blockage
        blockage_x = river_geom.centroid.x
        blockage_width = params.get("blockage_width", 50.0)
        blockage_height = params.get("blockage_height", 15.0)

        # Use thin dam to represent the blockage before failure
        sg = Delft3DStructureGenerator(self.workspace_path)

        blockage_polyline = [
            (blockage_x, ymin),
            (blockage_x, ymax)
        ]

        # Dambreak at blockage location — represents the failure of the natural dam
        breach_y = (ymin + ymax) / 2.0
        failure_time_s = params.get("failure_time", 1.0) * 3600

        # Use timeseries algorithm for controlled failure
        breach_width = params.get("breach_width", 30.0)
        formation_time_s = params.get("breach_formation_time", 0.5) * 3600 if params.get("breach_formation_time") else 1800

        breach_ts = [
            (0.0, 0.0),
            (failure_time_s, 0.0),
            (failure_time_s + 1.0, 5.0),  # Failure initiates
            (failure_time_s + formation_time_s, breach_width),
            (failure_time_s + formation_time_s * 2, breach_width)
        ]

        ini_path, pli_path = sg.generate_dambreak_structure(
            structure_id="blockage_failure",
            polyline_coords=blockage_polyline,
            start_location=(blockage_x, breach_y),
            crest_level_ini=blockage_height,
            algorithm=3,
            breach_timeseries=breach_ts
        )

        mdu_config["geometry"]["StructureFile"] = os.path.relpath(ini_path, self.workspace_path)

        # Upstream river inflow
        bg = Delft3DBoundaryGenerator(self.workspace_path)
        ext = Delft3DExtGenerator(self.workspace_path)

        us_coords = [(xmin, ymin + (ymax - ymin) * 0.3), (xmin, ymin + (ymax - ymin) * 0.7)]
        us_pli = bg.generate_boundary_polyline("upstream", us_coords)
        us_nodes = [f"upstream_{i+1:04d}" for i in range(len(us_coords))]

        river_q = params.get("river_discharge", params.get("initial_discharge", 100.0))
        duration_mins = self._get_time_params().get("duration_hours", 24) * 60
        us_ts = Delft3DBoundaryGenerator.generate_constant_discharge(river_q, duration_mins)
        us_bc = bg.generate_discharge_bc("upstream", us_ts, us_nodes)

        us_pli_rel = os.path.relpath(us_pli, os.path.join(self.workspace_path, "boundary"))
        us_bc_rel = os.path.relpath(us_bc, os.path.join(self.workspace_path, "boundary"))
        ext.add_boundary("dischargebnd", us_pli_rel, us_bc_rel)

        # Downstream open boundary
        ds_coords = [(xmax, ymin), (xmax, ymax)]
        ds_pli = bg.generate_boundary_polyline("downstream", ds_coords, "downstream.pli")
        ds_nodes = [f"downstream_{i+1:04d}" for i in range(len(ds_coords))]
        ds_wl = params.get("initial_downstream_condition", 0.0)
        ds_ts = [(0.0, ds_wl), (duration_mins, ds_wl)]
        ds_bc = bg.generate_waterlevel_bc("downstream", ds_ts, ds_nodes, "downstream.bc")
        ds_pli_rel = os.path.relpath(ds_pli, os.path.join(self.workspace_path, "boundary"))
        ds_bc_rel = os.path.relpath(ds_bc, os.path.join(self.workspace_path, "boundary"))
        ext.add_boundary("waterlevelbnd", ds_pli_rel, ds_bc_rel)

        ext_path = ext.generate()
        mdu_config["external forcing"] = {
            "ExtForceFileNew": os.path.relpath(ext_path, self.workspace_path)
        }

        # Initial water level — river level upstream
        mdu_config["geometry"]["WaterLevIni"] = params.get("initial_water_level", 2.0)

        self.metadata["scenario"] = {
            "type": "RIVER_BLOCKAGE",
            "blockage_height": blockage_height,
            "blockage_width": blockage_width,
            "failure_time_s": failure_time_s,
            "breach_algorithm": "Timeseries (Algorithm 3)"
        }

    def generate_mdu(self, rel_mesh_path: str) -> str:
        """Generates the D-Flow FM .mdu configuration file."""
        mdu_filename = "scenario.mdu"
        mdu_path = os.path.join(self.workspace_path, mdu_filename)

        time_params = self._get_time_params()
        duration_hours = time_params.get("duration_hours", 1.0)
        dt_user = time_params.get("timestep_seconds", 30.0)
        output_interval = self.context.scenario.output_interval or 600

        mdu_config = {
            "General": {
                "Program": "D-Flow FM",
                "Version": "1.2.184",
                "AutoStart": "0",
                "FileVersion": "1.02",
                "PathsRelativeToParent": "0"
            },
            "geometry": {
                "NetFile": rel_mesh_path,
                "WaterLevIni": 0.0,
                "BedlevType": 3,
                "BedlevMode": 1,
                "Kmx": 0,  # 2D depth-averaged
                "OpenBoundaryTolerance": 3,
                "RenumberFlowNodes": 1,
                "UseCaching": 1,
                "StructureFile": "",
                "LandBoundaryFile": "",
                "ThinDamFile": ""
            },
            "numerics": {
                "CFLMax": 0.7,
                "AdvecType": 33,
                "TimeStepType": 2,
                "Teta0": 0.55,
                "Epshu": 0.0001,
                "Limtypmom": 4,
                "Icgsolver": 4,
                "MaxDegree": 6,
                "FixedWeirScheme": 6
            },
            "physics": {
                "UnifFrictCoef": 0.023,
                "UnifFrictType": 1,  # Manning
                "Vicouv": 1.0
            },
            "time": {
                "RefDate": "20240101",
                "Tunit": "S",
                "DtUser": dt_user,
                "TStart": 0.0,
                "TStop": duration_hours * 3600
            },
            "output": {
                "OutputDir": "output",
                "HisInterval": str(int(output_interval)),
                "MapInterval": str(int(output_interval)),
                "Wrimap_waterlevel_s1": 1,
                "Wrimap_velocity_vector": 1,
                "Wrimap_velocity_component_u1": 1,
                "Wrimap_waterlevel_s0": 0,
                "Wrimap_velocity_component_u0": 0,
                "Wrihis_waterlevel_s1": 1,
                "Wrihis_velocity_vector": 1,
                "Wrihis_structure_dam": 1,
                "Wrihis_structure_gen": 1
            }
        }

        # Apply scenario-specific configuration
        scenario_type = self._get_scenario_type()
        logger.info(f"Building MDU for scenario type: {scenario_type}")

        if scenario_type == "DAM_BREAK":
            self._build_dam_break(mdu_config)
        elif scenario_type in ("WATER_RELEASE", "CONTROLLED_RELEASE"):
            self._build_controlled_release(mdu_config)
        elif scenario_type == "RIVER_BLOCKAGE":
            self._build_river_blockage(mdu_config)
        else:
            raise ValueError(f"Unknown scenario type: {scenario_type}")

        # Apply terrain if available
        terrain_rel = self._build_terrain()
        if terrain_rel:
            mdu_config["geometry"]["BathymetryFile"] = terrain_rel

        # Write MDU
        with open(mdu_path, "w") as f:
            for section, fields in mdu_config.items():
                f.write(f"[{section}]\n")
                for key, val in fields.items():
                    # Skip empty string values
                    if isinstance(val, str) and val == "":
                        continue
                    f.write(f"{key.ljust(38)} = {val}\n")
                f.write("\n")

        logger.info(f"MDU written to {mdu_path}")
        return mdu_filename

    def build(self, mock: bool = False) -> str:
        """Executes the full build pipeline and returns the MDU filename."""
        self.prepare_workspace()

        # 1. Generate computational mesh
        rel_mesh_path = self._build_mesh()

        # 2. Build MDU with scenario-specific config, terrain, boundaries
        mdu_filename = self.generate_mdu(rel_mesh_path)

        # 3. Write metadata
        self._write_metadata()

        return mdu_filename

    def _write_metadata(self) -> None:
        """Writes simulation metadata to the workspace."""
        import json
        meta_path = os.path.join(self.workspace_path, "metadata", "build_info.json")
        self.metadata["build_time"] = datetime.utcnow().isoformat()
        self.metadata["simulation_id"] = self.simulation_id
        self.metadata["delft3d_version"] = "D-Flow FM 1.2.184"
        self.metadata["physical_model"] = "2D depth-averaged shallow water equations (Kmx=0)"
        self.metadata["config"] = self.params

        with open(meta_path, "w") as f:
            json.dump(self.metadata, f, indent=2, default=str)
