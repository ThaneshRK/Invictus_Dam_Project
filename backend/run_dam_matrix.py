#!/usr/bin/env python3
"""
Dam Break Scenario Matrix Runner — 5 dams x 3 scenarios x 2 engines.

Runs the complete deliverable matrix WITHOUT requiring the API/DB stack:

  Dams       : Bhakra, Tehri, Hirakud, Sardar Sarovar, Mettur
               (static government fixtures in data/fixtures/government/)
  Scenarios  : DAM_BREAK, WATER_RELEASE (controlled release), RIVER_BLOCKAGE
  Engines    : SPH 3D (true 3D WCSPH, internal solver)
               Delft3D-FM (full workspace build: mesh/MDU/structures/forcing;
                           executed only when the dflowfm binary is installed)

Outputs (under data/matrix_results/):
  {dam}/{scenario}/sph3d_result.json        - metrics + diagnostics
  {dam}/{scenario}/sph3d_inundation.geojson - max-depth footprint (WGS84)
  {dam}/{scenario}/sph3d_max_depth.tif      - max depth raster (UTM)
  {dam}/{scenario}/delft3d_status.json      - workspace status/file inventory
  {dam}/inputs/dem.tif                      - terrain used (real or synthetic)
  matrix_summary.json                       - machine-readable matrix
  matrix_report.md                          - human-readable 5x3 matrix report

Usage:
  .venv/bin/python backend/run_dam_matrix.py                # full matrix
  .venv/bin/python backend/run_dam_matrix.py --dams tehri   # subset
  .venv/bin/python backend/run_dam_matrix.py --scenarios DAM_BREAK --engines SPH3D
"""
import argparse
import json
import logging
import math
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import reproject, Resampling

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.engines.sph.engine import SPHEngine                      # noqa: E402
from app.engines.sph.boundary import TerrainHandler               # noqa: E402
from app.engines.delft3d.builder import Delft3DModelBuilder       # noqa: E402
from app.engines.delft3d.executor import HostDelft3DExecutor      # noqa: E402
from app.engines.delft3d.parser import Delft3DResultParser        # noqa: E402

import shapely.geometry                                            # noqa: E402
import shapely.ops                                                 # noqa: E402
from geoalchemy2.shape import from_shape                          # noqa: E402
from pyproj import Transformer                                    # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("dam_matrix")

FIXTURE_ROOT = REPO_ROOT / "data" / "fixtures" / "government"
OUT_ROOT = REPO_ROOT / "data" / "matrix_results"
REAL_TEHRI_DEM = REPO_ROOT / "tests" / "data_real" / "copernicus_dem_tehri.tif"

DAM_ORDER = ["bhakra", "tehri", "hirakud", "sardar_sarovar", "mettur"]
SCENARIOS = ["DAM_BREAK", "WATER_RELEASE", "RIVER_BLOCKAGE"]

DOMAIN_HALF = 700.0          # m; domain is 1.4 km x 1.4 km around the dam
DEM_RES = 10.0               # m per cell
TARGET_SPH_PARTICLES = 9000  # 3D particle budget per run

# ---------------------------------------------------------------- fixtures


def load_dam_system(dam_id: str) -> dict:
    dam = json.loads((FIXTURE_ROOT / "dams" / f"{dam_id}.json").read_text())
    hydro = json.loads((FIXTURE_ROOT / "hydrology" / f"{dam_id}.json").read_text())
    return {"id": dam_id, "dam": dam, "hydrology": hydro}


def latest_hydro_values(hydro: dict) -> dict:
    """Pulls the most recent water level / inflow / outflow from the fixture."""
    out = {"water_level": None, "inflow": None, "outflow": None}
    obs = hydro.get("observations") or []
    for o in obs:
        for key in out:
            entry = o.get(key)
            if isinstance(entry, dict) and entry.get("value") is not None:
                out[key] = float(entry["value"])
    return out


# ---------------------------------------------------------------- terrain


def utm_epsg_for_lon(lon: float) -> int:
    zone = int((lon + 180.0) // 6) + 1
    return 32600 + zone  # northern hemisphere


def domain_bounds_for(dam_lon: float, dam_lat: float, epsg: int) -> tuple:
    """1.4 km UTM box centred on the dam."""
    tf = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    dx, dy = tf.transform(dam_lon, dam_lat)
    return (dx - DOMAIN_HALF, dy - DOMAIN_HALF, dx + DOMAIN_HALF, dy + DOMAIN_HALF), (dx, dy)


def build_synthetic_dem(bounds: tuple, dam_xy: tuple, z0: float) -> np.ndarray:
    """
    Schematic valley DEM (metres, UTM):
      - river axis runs west->east, dam at dam_xy (north-south wall line)
      - reservoir basin upstream (west), steeper gorge downstream (east)
      - parabolic valley walls
    Returns the elevation array; the caller persists it via write_dem().
    """
    xmin, ymin, xmax, ymax = bounds
    nx = int(round((xmax - xmin) / DEM_RES))
    ny = int(round((ymax - ymin) / DEM_RES))
    xs = np.linspace(xmin + DEM_RES / 2, xmax - DEM_RES / 2, nx)
    ys = np.linspace(ymax - DEM_RES / 2, ymin + DEM_RES / 2, ny)  # north -> south rows
    xx, yy = np.meshgrid(xs, ys)

    dam_x, dam_y = dam_xy
    dx = xx - dam_x
    dy = np.abs(yy - dam_y)

    bed = np.where(
        dx <= 0,
        z0 + 0.004 * (-dx),              # gentle upstream basin slope
        z0 - 0.018 * dx,                 # steeper downstream gorge
    )
    half_width = np.where(dx <= 0, 350.0, 220.0)
    walls = 90.0 * (dy / half_width) ** 2
    return (bed + walls).astype(np.float32)


def write_dem(array: np.ndarray, bounds: tuple, epsg: int, out_path: Path) -> None:
    ny, nx = array.shape
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        out_path, "w", driver="GTiff", height=ny, width=nx, count=1,
        dtype="float32", crs=f"EPSG:{epsg}",
        transform=from_origin(bounds[0], bounds[3], DEM_RES, DEM_RES),
    ) as dst:
        dst.write(array.astype(np.float32), 1)


def build_real_dem_clip(bounds: tuple, epsg: int, src_path: Path, out_path: Path) -> bool:
    """Reprojects a window of a real DEM to the UTM domain at DEM_RES."""
    try:
        with rasterio.open(src_path) as src:
            nx = int(round((bounds[2] - bounds[0]) / DEM_RES))
            ny = int(round((bounds[3] - bounds[1]) / DEM_RES))
            dst_crs = f"EPSG:{epsg}"
            transform = from_origin(bounds[0], bounds[3], DEM_RES, DEM_RES)
            data = np.full((ny, nx), np.nan, dtype=np.float32)
            reproject(
                source=rasterio.band(src, 1), destination=data,
                src_transform=src.transform, src_crs=src.crs,
                dst_transform=transform, dst_crs=dst_crs,
                resampling=Resampling.bilinear,
            )
        if np.all(np.isnan(data)):
            return False
        data = np.where(np.isnan(data), np.nanmedian(data), data)
        write_dem(data, bounds, epsg, out_path)
        return True
    except Exception as err:
        logger.warning(f"Real DEM clip failed ({err}); falling back to synthetic.")
        return False


# ---------------------------------------------------------------- contexts




def pick_water_level(terrain: TerrainHandler, water_box: list, head: float) -> float:
    """
    Chooses an initial water surface elevation:
    the reservoir/lake bed (5th-percentile terrain, robust to outlier cells) plus
    the scenario head, raised until >= 50% of the box is wet.
    Depth at the channel is therefore ~head, as intended per dam.
    """
    xmin, xmax, ymin, ymax = water_box
    gx = np.arange(xmin, xmax, 10.0)
    gy = np.arange(ymin, ymax, 10.0)
    xx, yy = np.meshgrid(gx, gy)
    pts = np.vstack([xx.ravel(), yy.ravel()]).T
    z_b, _ = terrain.get_elevation_and_gradient(pts)
    wl = float(np.percentile(z_b, 5)) + head
    for _ in range(8):
        if np.mean(z_b < wl) >= 0.5:
            break
        wl += 4.0
    return wl


def count_3d_particles(terrain: TerrainHandler, water_box: list, wl: float, spacing: float) -> int:
    xmin, xmax, ymin, ymax = water_box
    gx = np.arange(xmin, xmax, spacing)
    gy = np.arange(ymin, ymax, spacing)
    xx, yy = np.meshgrid(gx, gy)
    pts = np.vstack([xx.ravel(), yy.ravel()]).T
    z_b, _ = terrain.get_elevation_and_gradient(pts)
    depths = wl - z_b[z_b < wl]
    if len(depths) == 0:
        return 0
    return int(np.sum(np.ceil(depths / spacing)))


def choose_spacing(terrain: TerrainHandler, water_box: list, wl: float,
                   start: float = 6.0, cap: float = 18.0) -> float:
    spacing = start
    while spacing < cap and count_3d_particles(terrain, water_box, wl, spacing) > TARGET_SPH_PARTICLES:
        spacing += 2.0
    return spacing


class ScenarioSpec:
    """Per-(dam, scenario) configuration: geometry + parameters for both engines."""

    def __init__(self, name, scenario_type, water_box, blockage_box, params,
                 duration_hours, duration_cap_s, dem_path, dam_xy, epsg, wl):
        self.name = name
        self.scenario_type = scenario_type
        self.water_box = water_box
        self.blockage_box = blockage_box
        self.params = params
        self.duration_hours = duration_hours
        self.duration_cap_s = duration_cap_s
        self.dem_path = dem_path
        self.dam_xy = dam_xy
        self.epsg = epsg
        self.wl = wl

    # -- objects shaped like the SimulationInputContext the engines expect --
    def context(self):
        dam_x, dam_y = self.dam_xy
        xmin, xmax, ymin, ymax = self.water_box
        return SimpleNamespace(
            project=SimpleNamespace(id="matrix-runner", name="5x3 Matrix"),
            scenario=SimpleNamespace(
                scenario_type=SimpleNamespace(value=self.scenario_type),
                simulation_duration=self.duration_hours,
                timestep=1.0,
                output_interval=600.0,
                parameters=dict(self.params),
            ),
            dem=SimpleNamespace(metadata={"file_path": str(self.dem_path)}),
            hydrology=None,
            dam=SimpleNamespace(geometry=from_shape(shapely.geometry.Point(dam_x, dam_y), srid=self.epsg)),
            reservoir=SimpleNamespace(
                geometry=from_shape(shapely.geometry.box(xmin, ymin, xmax, ymax), srid=self.epsg)
            ),
            river=SimpleNamespace(
                geometry=from_shape(
                    shapely.geometry.box(*self.blockage_box) if self.blockage_box
                    else shapely.geometry.Point(dam_x + 300.0, dam_y),
                    srid=self.epsg,
                )
            ),
            study_area=None,
        )


def build_specs(system: dict, dem_path: Path, epsg: int, bounds: tuple,
                dam_xy: tuple, dem_source: str) -> list:
    """Builds the three ScenarioSpecs for one dam from its static fixture data."""
    dam = system["dam"]
    hydro = latest_hydro_values(system["hydrology"])
    dam_x, dam_y = dam_xy

    terrain = TerrainHandler.from_geotiff(str(dem_path))
    dam_height = float(dam.get("dam_height_m") or 100.0)
    dam_length = float(dam.get("dam_length_m") or 300.0)
    # Prototype-scale head: scaled from the real dam height but capped so the
    # 1.4 km demo domain and particle budget stay meaningful (per-dam differentiated).
    head = min(0.15 * dam_height, 30.0)
    # Breach width: USBR-style empirical relation (avg ≈ 3x dam height), capped for the domain.
    breach_width = min(3.0 * dam_height, 140.0)

    reservoir_box = [dam_x - 600.0, dam_x - 40.0, dam_y - 250.0, dam_y + 250.0]
    lake_box = [dam_x + 80.0, dam_x + 520.0, dam_y - 150.0, dam_y + 150.0]
    blockage_box = [dam_x + 540.0, dam_x + 580.0, dam_y - 200.0, dam_y + 200.0]

    wl_res = pick_water_level(terrain, reservoir_box, head)
    wl_lake = pick_water_level(terrain, lake_box, min(head, 12.0))
    spacing_res = choose_spacing(terrain, reservoir_box, wl_res)
    spacing_lake = choose_spacing(terrain, lake_box, wl_lake)

    inflow_q = hydro.get("inflow") or 250.0
    outflow_q = hydro.get("outflow") or 300.0

    specs = []

    # 1) Catastrophic dam break
    specs.append(ScenarioSpec(
        name=f"{dam['dam_name']} - Catastrophic Dam Break",
        scenario_type="DAM_BREAK",
        water_box=reservoir_box, blockage_box=None,
        params={
            "dimensions": 3,
            "initial_water_level": wl_res,
            "breach_width": breach_width,
            "failure_time": 2.0,
            "formation_time": 6.0,
            "particle_spacing": spacing_res,
            "smoothing_length": 1.3 * spacing_res,  # standard cubic-spline kernel ratio
            "duration_cap_s": 10.0,
            # Delft3D-FM parameters (absolute levels, hours for formation)
            "mesh_resolution": 25.0,
            "breach_elevation": wl_res + 2.0,
            "crest_level_min": wl_res - head - 2.0,
            "breach_formation_time": 1.0,
        },
        duration_hours=2.0, duration_cap_s=10.0,
        dem_path=dem_path, dam_xy=dam_xy, epsg=epsg, wl=wl_res,
    ))

    # 2) Controlled release (spillway gates)
    specs.append(ScenarioSpec(
        name=f"{dam['dam_name']} - Controlled Release",
        scenario_type="WATER_RELEASE",
        water_box=reservoir_box, blockage_box=None,
        params={
            "dimensions": 3,
            "initial_water_level": wl_res,
            "breach_width": breach_width,
            "release_width": max(12.0, 0.15 * breach_width),
            "failure_time": 1.0,
            "formation_time": 3.0,
            "particle_spacing": spacing_res,
            "smoothing_length": 1.3 * spacing_res,  # standard cubic-spline kernel ratio
            "duration_cap_s": 8.0,
            # Delft3D-FM parameters
            "mesh_resolution": 25.0,
            "peak_discharge": outflow_q,
            "initial_discharge": 0.2 * outflow_q,
            "release_duration": 1.5,
            "initial_downstream_condition": 0.1,
        },
        duration_hours=2.0, duration_cap_s=8.0,
        dem_path=dem_path, dam_xy=dam_xy, epsg=epsg, wl=wl_res,
    ))

    # 3) River blockage (landslide dam in the downstream gorge)
    specs.append(ScenarioSpec(
        name=f"{dam['dam_name']} - River Blockage / Landslide Dam Outburst",
        scenario_type="RIVER_BLOCKAGE",
        water_box=lake_box, blockage_box=blockage_box,
        params={
            "dimensions": 3,
            "initial_water_level": wl_lake,
            "breach_width": breach_width,
            "failure_time": 4.0,          # SPH: blockage removal time (s)
            "formation_time": 3.0,
            "particle_spacing": spacing_lake,
            "smoothing_length": 1.3 * spacing_lake,
            "duration_cap_s": 10.0,
            # Delft3D-FM parameters (failure_time in hours for the structure)
            "mesh_resolution": 25.0,
            "blockage_width": 40.0,
            "blockage_height": wl_lake + 6.0,
            "breach_formation_time": 0.5,
            "river_discharge": inflow_q,
            "failure_time_hours": 0.5,
        },
        duration_hours=2.0, duration_cap_s=10.0,
        dem_path=dem_path, dam_xy=dam_xy, epsg=epsg, wl=wl_lake,
    ))

    for s in specs:
        s.dem_source = dem_source
        s.dam_name = dam["dam_name"]
        s.hydro = hydro
    return specs


# ---------------------------------------------------------------- runners


def run_sph3d(spec: ScenarioSpec, run_dir: Path) -> dict:
    from app.engines.sph.engine import SPHEngine  # local import keeps CLI snappy
    t0 = time.time()
    engine = SPHEngine(spec.context(), use_3d=True)
    entry = {"engine": "SPH3D", "status": "FAILED", "error": None}

    if not engine.validate():
        entry["error"] = engine.error_message
        return entry
    engine.prepare()
    if engine.status == "FAILED":
        entry["error"] = engine.error_message
        return entry

    entry["particle_count"] = int(engine.solver.state.num_particles)
    engine.run()
    wall_s = round(time.time() - t0, 2)

    if engine.status != "COMPLETED":
        entry["error"] = engine.error_message
        entry["wall_time_s"] = wall_s
        return entry

    results = engine.load_results()
    depth = np.array(
        [[0.0 if v is None else float(v) for v in row] for row in results["max_depth_array"]],
        dtype=np.float64,
    )
    res_cell = abs(results["transform"][0])
    flooded = depth >= 0.1
    metrics = {
        "engine": "SPH3D",
        "status": "COMPLETED",
        "error": None,
        "particle_count": entry["particle_count"],
        "simulated_time_s": round(engine.solver.time, 2),
        "wall_time_s": wall_s,
        "max_depth_m": round(float(depth.max()), 2),
        "mean_depth_flooded_m": round(float(depth[flooded].mean()), 2) if flooded.any() else 0.0,
        "flooded_area_km2": round(float(flooded.sum()) * res_cell ** 2 / 1e6, 4),
        "grid_resolution_m": res_cell,
        "initial_water_level_m": round(spec.wl, 2),
        "diagnostics": engine.diagnostics,
        "metadata": results["metadata"],
    }

    # Max-depth raster (UTM)
    run_dir.mkdir(parents=True, exist_ok=True)
    tif_path = run_dir / "sph3d_max_depth.tif"
    ny, nx = depth.shape
    b = results["bounds"]
    with rasterio.open(
        tif_path, "w", driver="GTiff", height=ny, width=nx, count=1,
        dtype="float32", crs=f"EPSG:{spec.epsg}", nodata=-9999.0,
        transform=rasterio.transform.from_origin(b[0], b[3], res_cell, res_cell),
    ) as dst:
        dst.write(np.where(flooded, depth, -9999.0).astype(np.float32), 1)

    # Inundation footprint in WGS84
    poly = results.get("inundation_polygon")
    if poly:
        tf = Transformer.from_crs(f"EPSG:{spec.epsg}", "EPSG:4326", always_xy=True)
        poly_wgs = shapely.ops.transform(lambda x, y, z=None: tf.transform(x, y), shapely.geometry.shape(poly))
        fc = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {
                    "dam": spec.dam_name, "scenario": spec.scenario_type, "engine": "SPH3D",
                    "max_depth_m": metrics["max_depth_m"],
                    "flooded_area_km2": metrics["flooded_area_km2"],
                },
                "geometry": poly_wgs.__geo_interface__,
            }],
        }
        (run_dir / "sph3d_inundation.geojson").write_text(json.dumps(fc))

    return metrics


def run_delft3d(spec: ScenarioSpec, workspaces_root: Path, execute: bool = True) -> dict:
    sim_id = f"{spec.dam_name.split()[0].lower()}_{spec.scenario_type.lower()}"
    entry = {"engine": "DELFT3D", "status": "FAILED", "error": None}
    try:
        builder = Delft3DModelBuilder(
            workspace_root=str(workspaces_root), simulation_id=sim_id, context=spec.context()
        )
        mdu_name = builder.build()
        entry["workspace"] = builder.workspace_path
        entry["mdu_file"] = mdu_name
        entry["files"] = sorted(
            os.path.relpath(os.path.join(dp, f), builder.workspace_path)
            for dp, _, files in os.walk(builder.workspace_path) for f in files
        )
        entry["build_metadata"] = builder.metadata.get("scenario")
    except Exception as err:
        entry["error"] = f"workspace build failed: {err}"
        logger.exception("Delft3D build failed")
        return entry

    executor = HostDelft3DExecutor(builder.workspace_path, mdu_name)
    if not executor.validate_installation():
        entry["status"] = "WORKSPACE_READY_NO_BINARY"
        entry["error"] = (
            "dflowfm binary not installed on this machine — full D-Flow FM workspace "
            "(mesh/MDU/structures/forcing) generated and ready to execute."
        )
        return entry

    if not execute:
        entry["status"] = "WORKSPACE_READY"
        return entry

    try:
        executor.start()
        code = executor.wait(timeout=1800)
        if code == 0:
            parser = Delft3DResultParser(builder.workspace_path)
            meta = parser.parse()
            entry["status"] = "COMPLETED"
            entry["max_depth_m"] = meta.get("max_water_depth")
            entry["outputs"] = meta.get("outputs", {})
        else:
            entry["status"] = "EXECUTION_FAILED"
            entry["error"] = executor.error_message
    except Exception as err:
        entry["status"] = "EXECUTION_FAILED"
        entry["error"] = str(err)
    return entry


# ---------------------------------------------------------------- main


def process_dam(dam_id: str, scenarios: list, engines: list, execute_delft3d: bool) -> dict:
    system = load_dam_system(dam_id)
    dam = system["dam"]
    lon, lat = float(dam["longitude"]), float(dam["latitude"])
    epsg = utm_epsg_for_lon(lon)
    bounds, dam_xy = domain_bounds_for(lon, lat, epsg)

    dem_path = OUT_ROOT / dam_id / "inputs" / "dem.tif"
    dem_source = "SYNTHETIC_VALLEY (schematic, prototype)"
    if dam_id == "tehri" and REAL_TEHRI_DEM.exists():
        if build_real_dem_clip(bounds, epsg, REAL_TEHRI_DEM, dem_path):
            dem_source = "REAL Copernicus GLO-30 clip (reprojected to UTM)"
    if not dem_path.exists():
        dem = build_synthetic_dem(bounds, dam_xy, z0=300.0)
        write_dem(dem, bounds, epsg, dem_path)

    specs = build_specs(system, dem_path, epsg, bounds, dam_xy, dem_source)
    dam_out = {
        "dam_id": dam_id,
        "dam_name": dam["dam_name"],
        "river": dam.get("river_name"),
        "state": dam.get("state"),
        "dam_height_m": dam.get("dam_height_m"),
        "gross_storage_bcm": dam.get("gross_storage_bcm"),
        "utm_epsg": epsg,
        "dem": {"path": str(dem_path), "source": dem_source, "resolution_m": DEM_RES},
        "hydrology_static": latest_hydro_values(system["hydrology"]),
        "scenarios": {},
    }

    for spec in specs:
        if spec.scenario_type not in scenarios:
            continue
        run_dir = OUT_ROOT / dam_id / spec.scenario_type
        run_dir.mkdir(parents=True, exist_ok=True)
        scen_out = {"name": spec.name, "params": spec.params}

        if "SPH3D" in engines:
            logger.info(f"[{dam_id}/{spec.scenario_type}] running SPH 3D ...")
            try:
                scen_out["SPH3D"] = run_sph3d(spec, run_dir)
            except Exception as err:
                scen_out["SPH3D"] = {"engine": "SPH3D", "status": "FAILED", "error": str(err)}
                logger.exception(f"SPH3D failed for {dam_id}/{spec.scenario_type}")

        if "DELFT3D" in engines:
            logger.info(f"[{dam_id}/{spec.scenario_type}] building Delft3D workspace ...")
            try:
                scen_out["DELFT3D"] = run_delft3d(
                    spec, OUT_ROOT / "delft3d_workspaces", execute=execute_delft3d
                )
            except Exception as err:
                scen_out["DELFT3D"] = {"engine": "DELFT3D", "status": "FAILED", "error": str(err)}
                logger.exception(f"Delft3D failed for {dam_id}/{spec.scenario_type}")

        (run_dir / "run_result.json").write_text(json.dumps(scen_out, indent=2, default=str))
        dam_out["scenarios"][spec.scenario_type] = scen_out

    return dam_out


def write_report(summary: dict, path: Path) -> None:
    lines = [
        "# Dam Break Scenario Matrix — 5 Dams x 3 Scenarios",
        "",
        f"_Generated: {datetime.now(timezone.utc).isoformat()} — by `backend/run_dam_matrix.py`_",
        "",
        "| Dam | Scenario | SPH 3D | Max depth (m) | Flooded (km²) | Particles | Delft3D-FM |",
        "|-----|----------|--------|---------------|---------------|-----------|------------|",
    ]
    status_icon = {
        "COMPLETED": "✅ COMPLETED",
        "WORKSPACE_READY_NO_BINARY": "🧱 workspace ready (no dflowfm binary)",
        "WORKSPACE_READY": "🧱 workspace ready",
        "FAILED": "❌ FAILED",
        "EXECUTION_FAILED": "❌ EXEC FAILED",
    }
    for dam in summary["dams"]:
        for scen in SCENARIOS:
            s = dam["scenarios"].get(scen)
            if not s:
                continue
            sph = s.get("SPH3D") or {}
            d3d = s.get("DELFT3D") or {}
            lines.append(
                f"| {dam['dam_name']} | {scen} "
                f"| {status_icon.get(sph.get('status'), sph.get('status', '—'))} "
                f"| {sph.get('max_depth_m', '—')} | {sph.get('flooded_area_km2', '—')} "
                f"| {sph.get('particle_count', '—')} "
                f"| {status_icon.get(d3d.get('status'), d3d.get('status', '—'))} |"
            )
    lines += [
        "",
        "## Terrain sources",
        "",
        "| Dam | DEM |",
        "|-----|-----|",
    ]
    for dam in summary["dams"]:
        lines.append(f"| {dam['dam_name']} | {dam['dem']['source']} |")
    lines += [
        "",
        "## Notes",
        "",
        "- **SPH 3D** runs are true 3D weakly-compressible SPH (Tait EOS, 3D cubic-spline",
        "  kernel, 3D artificial viscosity, terrain collision) executed by the internal",
        "  solver in `backend/app/engines/sph/`.",
        "- **Delft3D-FM** entries with status `workspace ready` contain a complete D-Flow FM",
        "  workspace (UGRID mesh `_net.nc`, `.mdu`, structure `.ini`, boundary `.pli/.bc/.ext`).",
        "  They execute automatically once a `dflowfm` installation is present",
        "  (`DELFT3D_INSTALL_DIR` in `backend/app/core/config.py`), or run the workspace",
        "  manually with `dflowfm --autostartstop <mdu>`.",
        "- Scenario physics: DAM_BREAK = full-breach failure of the dam wall;",
        "  WATER_RELEASE = spillway gate opening (narrow release width) / Q(t) boundary in",
        "  Delft3D; RIVER_BLOCKAGE = landslide blockage in the downstream gorge failing at",
        "  t = failure_time (SPH) / dambreak structure timeseries (Delft3D).",
        "- Prototype limits: SPH runs are capped at 8-15 s of simulated time and ~9k",
        "  particles; heads are scaled to 15% of the real dam height (max 30 m) so the demo",
        "  domain (1.4 km) stays meaningful. Real operational studies need larger domains,",
        "  real bathymetry and no caps.",
    ]
    path.write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description="5 dams x 3 scenarios x 2 engines matrix runner")
    ap.add_argument("--dams", nargs="*", default=DAM_ORDER, choices=DAM_ORDER)
    ap.add_argument("--scenarios", nargs="*", default=SCENARIOS, choices=SCENARIOS)
    ap.add_argument("--engines", nargs="*", default=["SPH3D", "DELFT3D"], choices=["SPH3D", "DELFT3D"])
    ap.add_argument("--no-delft3d-execute", action="store_true",
                    help="Build Delft3D workspaces but never execute them")
    args = ap.parse_args()

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    summary = {"generated_at": datetime.now(timezone.utc).isoformat(), "dams": []}

    for dam_id in args.dams:
        try:
            summary["dams"].append(
                process_dam(dam_id, args.scenarios, args.engines,
                            execute_delft3d=not args.no_delft3d_execute)
            )
        except Exception:
            logger.exception(f"Dam {dam_id} failed entirely")
            summary["dams"].append({"dam_id": dam_id, "dam_name": dam_id,
                                    "error": traceback.format_exc(limit=3), "scenarios": {}})

    (OUT_ROOT / "matrix_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    write_report(summary, OUT_ROOT / "matrix_report.md")

    # Console matrix
    print("\n================ MATRIX SUMMARY ================")
    for dam in summary["dams"]:
        for scen, s in dam.get("scenarios", {}).items():
            sph = s.get("SPH3D") or {}
            d3d = s.get("DELFT3D") or {}
            print(f"{dam['dam_name']:>20} | {scen:<15} | SPH3D: {sph.get('status', '—'):<10} "
                  f"maxdepth={sph.get('max_depth_m', '—')}m area={sph.get('flooded_area_km2', '—')}km² "
                  f"| Delft3D: {d3d.get('status', '—')}")
    print(f"Report: {OUT_ROOT / 'matrix_report.md'}")


if __name__ == "__main__":
    main()
