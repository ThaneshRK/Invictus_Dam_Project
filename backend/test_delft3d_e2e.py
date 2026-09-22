import os
import uuid
import rasterio
from rasterio.transform import from_origin
import numpy as np

from app.engines.delft3d.engine import Delft3DEngine

def create_synthetic_dem(filepath: str, bounds=(0, 0, 1000, 1000), res=10):
    """Creates a simple sloping DEM for testing."""
    xmin, ymin, xmax, ymax = bounds
    cols = int((xmax - xmin) / res)
    rows = int((ymax - ymin) / res)
    transform = from_origin(xmin, ymax, res, res)
    
    # Create a sloping terrain from 50m down to 10m
    data = np.linspace(50, 10, cols).reshape(1, -1)
    data = np.repeat(data, rows, axis=0).astype(np.float32)
    
    with rasterio.open(
        filepath,
        'w',
        driver='GTiff',
        height=rows,
        width=cols,
        count=1,
        dtype=data.dtype,
        crs='+proj=latlong',
        transform=transform,
    ) as dst:
        dst.write(data, 1)

def run_test():
    # 1. Create a DEM
    dem_path = "test_dem.tif"
    create_synthetic_dem(dem_path)
    
    # 2. Configure a real test scenario
    config = {
        "scenario_type": "DAM_BREAK",
        "bounds": [100.0, 100.0, 900.0, 900.0],
        "mesh_resolution": 100.0,
        "initial_water_level": 40.0,
        "physics_parameters": {
            "peak_discharge": 1000.0,
            "time_to_peak": 10.0,
            "duration": 60.0
        },
        "time_control": {
            "duration_hours": 0.1 # Very short run for testing
        },
        "source_datasets": [
            {"dataset_type": "DEM", "file_path": dem_path}
        ]
    }
    
    # 3. Instantiate Engine
    engine = Delft3DEngine(config)
    engine.simulation_id = str(uuid.uuid4())
    engine.workspace_root = "/tmp/delft3d_test"
    
    print("Preparing Workspace (Building Mesh, Terrain, Boundaries, MDU)...")
    engine.prepare()
    print(f"Prepare Status: {engine.status}")
    if engine.status == "FAILED":
        print(engine.error_message)
        return
        
    print("Running D-Flow FM...")
    engine.run()
    
    # Wait for completion
    import time
    while engine.status == "RUNNING":
        time.sleep(1)
        engine.get_status()
        
    print(f"Run Status: {engine.status}")
    if engine.status == "FAILED":
        print(engine.error_message)
        with open(engine.executor.stderr_log, 'r') as f:
            print("STDERR:")
            print(f.read())
            
    print("Loading Results...")
    res = engine.load_results()
    print("Result Data:", res)

if __name__ == "__main__":
    run_test()
