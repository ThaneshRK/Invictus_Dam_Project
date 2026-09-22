import pytest
from app.services.inundation_service import InundationService

def test_inundation_service_stats():
    # Mock engine output
    engine_results = {
        "max_depth_array": [
            [0.0, 0.0, 0.0],
            [0.05, 0.2, 0.5],
            [0.0, 1.0, 2.0]
        ]
    }
    
    # Process with 0.1m threshold
    results = InundationService.process_engine_output(engine_results, threshold_m=0.1)
    
    stats = results["stats"]
    assert stats["max_depth_m"] == 2.0
    # Values > 0.1 are 0.2, 0.5, 1.0, 2.0. (mean = 3.7 / 4 = 0.925)
    assert stats["mean_depth_m"] == 0.925
    # 4 cells * 4m2 / 1000000
    assert stats["inundated_area_km2"] == 1.6e-05
