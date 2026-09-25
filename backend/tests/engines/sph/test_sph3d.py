"""
End-to-end test for the true 3D SPH (WCSPH) engine path.

Verifies:
  1. SPHEngine(use_3d=True) selects the SPH3DSolver and prepares 3D particles
  2. The simulation runs to completion (terrain collision + Tait pressure + 3D viscosity)
  3. Results are spatialized onto the 2D inundation grid (max depth / arrival time)
  4. Particle mass is conserved during the run
"""
import os
import numpy as np
import rasterio
from rasterio.transform import from_origin

import shapely.geometry
from geoalchemy2.shape import from_shape

from app.engines.sph.engine import SPHEngine
from app.engines.sph.solver import SPH3DSolver


def create_valley_dem(filepath: str):
    """V-shaped valley DEM: 200x200 cells of 2 m, sloping downstream (+y)."""
    res = 2.0
    transform = from_origin(0, 200 * res, res, res)

    x = np.linspace(0, 400, 200)
    y = np.linspace(0, 400, 200)
    xx, yy = np.meshgrid(x, y)

    # Valley floor along x=200, rising to the sides; gentle downstream slope
    dem = np.abs(xx - 200) * 0.5 + yy * 0.1

    with rasterio.open(
        filepath, 'w',
        driver='GTiff', height=200, width=200, count=1,
        dtype=dem.dtype, crs='EPSG:4326', transform=transform, nodata=-9999.0
    ) as dst:
        dst.write(dem, 1)


def make_context(dem_path: str):
    class MockContext:
        class MockScenario:
            class ScenarioType:
                value = "DAM_BREAK"
            scenario_type = ScenarioType()
            simulation_duration = 1.0  # hours; capped by duration_cap_s
            parameters = {
                "particle_spacing": 4.0,
                "smoothing_length": 8.0,
                "initial_water_level": 55.0,
                "failure_time": 0.05,
                "formation_time": 0.2,
                "breach_width": 40.0,
                "duration_cap_s": 0.6,
            }
        scenario = MockScenario()

        class MockDataset:
            def __init__(self, metadata):
                self.metadata = metadata
        dem = MockDataset({"file_path": dem_path})
        hydrology = None

        class MockGeom:
            def __init__(self, x, y):
                self.geometry = from_shape(shapely.geometry.Point(x, y))

        class MockReservoir:
            def __init__(self, minx, miny, maxx, maxy):
                self.geometry = from_shape(shapely.geometry.box(minx, miny, maxx, maxy))

        dam = MockGeom(200.0, 200.0)
        river = MockGeom(200.0, 200.0)
        reservoir = MockReservoir(180.0, 240.0, 220.0, 300.0)

    return MockContext()


def test_sph3d_engine_lifecycle(tmp_path):
    dem_path = str(tmp_path / "valley3d.tif")
    create_valley_dem(dem_path)

    engine = SPHEngine(make_context(dem_path), use_3d=True)
    assert engine.validate()

    engine.prepare()
    assert engine.status == "PREPARED", f"prepare failed: {engine.error_message}"
    assert engine.use_3d is True
    assert isinstance(engine.solver, SPH3DSolver)
    assert engine.solver.dim == 3
    assert engine.solver.state.pos.shape[1] == 3

    n_before = engine.solver.state.num_particles
    assert n_before > 0
    mass_before = float(np.sum(engine.solver.state.mass[:n_before]))

    engine.run()
    assert engine.status == "COMPLETED", f"run failed: {engine.error_message}"

    # Mass conservation (particles are neither created nor destroyed)
    n_after = engine.solver.state.num_particles
    mass_after = float(np.sum(engine.solver.state.mass[:n_after]))
    assert n_after == n_before
    assert abs(mass_after - mass_before) / mass_before < 1e-9

    results = engine.load_results()
    assert results["metadata"]["solver_dimensionality"] == 3
    assert "3D" in results["metadata"]["sph_formulation"]

    depth = np.array(
        [[0.0 if v is None else v for v in row] for row in results["max_depth_array"]],
        dtype=float,
    )
    # Water must have spread: some cells deeper than the 0.05 m inundation threshold
    assert np.any(depth > 0.05), "3D run produced no inundation"
    assert np.isfinite(depth).all()


def test_sph3d_selected_via_scenario_parameter(tmp_path):
    """{"dimensions": 3} in scenario parameters must also select the 3D solver."""
    dem_path = str(tmp_path / "valley3d_b.tif")
    create_valley_dem(dem_path)

    ctx = make_context(dem_path)
    ctx.MockScenario.parameters = dict(ctx.MockScenario.parameters, dimensions=3)

    engine = SPHEngine(ctx)  # no explicit flag
    assert engine.use_3d is True
    engine.prepare()
    assert engine.status == "PREPARED"
    assert isinstance(engine.solver, SPH3DSolver)
