import pytest
from app.services.comparison_service import ComparisonService

def test_comparison_metric_correctness():
    # Simple arrays
    sph_data = {
        "max_depth_array": [[1.0, 2.0], [0.0, 0.5]]
    }
    d3d_data = {
        "max_depth_array": [[1.1, 1.9], [0.1, 0.0]]
    }
    
    result = ComparisonService.compare_results(sph_data, d3d_data)
    assert result["status"] == "success"
    
    metrics = result["metrics"]
    # Union area is 4 cells. 
    # MAE of union: |1.0-1.1| + |2.0-1.9| + |0-0.1| + |0.5-0| = 0.1 + 0.1 + 0.1 + 0.5 = 0.8
    # 0.8 / 4 = 0.2
    assert abs(metrics["depth_mae"] - 0.2) < 0.001

def test_comparison_missing_delft3d():
    sph_data = {"max_depth_array": [[1.0]]}
    d3d_data = {}
    
    result = ComparisonService.compare_results(sph_data, d3d_data)
    assert result["status"] == "partial"
    assert "unavailable" in result["message"]
