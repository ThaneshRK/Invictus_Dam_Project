import pytest
import numpy as np
import rasterio
from rasterio.transform import from_origin
import os
from app.engines.sph.engine import SPHEngine

def create_synthetic_dem(filepath: str):
    # 100x100 grid, cell size 2m, origin (0, 100) -> so Y goes from 100 down to 0, X from 0 to 200
    res = 2.0
    transform = from_origin(0, 100 * res, res, res)
    
    # Create a simple V-shaped valley
    x = np.linspace(0, 200, 100)
    y = np.linspace(0, 200, 100)
    xx, yy = np.meshgrid(x, y)
    
    # Elevation: higher on sides (x=0 and x=200), lower in middle (x=100)
    # Z = abs(x - 100) * 0.5 + y * 0.1
    dem = np.abs(xx - 100) * 0.5 + yy * 0.1
    
    with rasterio.open(
        filepath, 'w',
        driver='GTiff',
        height=100,
        width=100,
        count=1,
        dtype=dem.dtype,
        crs='EPSG:4326',
        transform=transform,
        nodata=-9999.0
    ) as dst:
        dst.write(dem, 1)

def test_sph_level_3_terrain():
    dem_path = "test_dem.tif"
    create_synthetic_dem(dem_path)
    
    config = {
        "metadata": {
            "type": "DAM_BREAK",
            "is_benchmark": False
        },
        "source_datasets": [
            {
                "dataset_type": "DEM",
                "file_path": dem_path
            }
        ],
        "physics_parameters": {
            "particle_spacing": 2.0,
            "smoothing_length": 4.0,
            "initial_water_polygon": [90.0, 110.0, 180.0, 200.0], # Valley top
            "initial_water_level": 30.0, # Will fill the valley up to Z=30
            "failure_time": 0.0,
            "formation_time": 0.1,
            "final_breach_width": 20.0
        },
        "time_control": {
            "duration_hours": 0.0005 # ~1.8 seconds simulation
        }
    }
    
    engine = SPHEngine(config)
    assert engine.validate()
    engine.prepare()
    assert engine.status == "PREPARED"
    
    assert engine.solver.state.num_particles > 0
    assert engine.solver.terrain_handler is not None
    
    engine.run()
    
    assert engine.status == "COMPLETED", f"Engine failed: {engine.error_message}"
    
    # Check diagnostics
    diags = engine.diagnostics
    assert "relative_volume_error" in diags
    assert abs(diags["relative_volume_error"]) < 0.05
    
    # Clean up
    if os.path.exists(dem_path):
        os.remove(dem_path)
