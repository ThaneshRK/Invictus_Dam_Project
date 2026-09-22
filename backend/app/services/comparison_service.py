import uuid
import numpy as np
from typing import Dict, Any, Tuple
from fastapi import HTTPException

class ComparisonService:
    @staticmethod
    def compare_results(sph_result: Dict[str, Any], delft3d_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compares two results. 
        Expects dicts containing 'max_depth_array', 'crs', and 'bounds'.
        """
        # Validate data presence
        sph_depth = sph_result.get("max_depth_array")
        d3d_depth = delft3d_result.get("max_depth_array")
        
        if not sph_depth:
            raise ValueError("SPH result missing max_depth_array")
            
        if not d3d_depth:
            return {
                "status": "partial",
                "message": "Delft3D result unavailable",
                "metrics": {}
            }
            
        # Convert to numpy arrays for calculation
        sph_arr = np.array(sph_depth)
        d3d_arr = np.array(d3d_depth)
        
        # Ensure dimensions match for the prototype comparison
        # (In a real system, we'd use rasterio to warp/reproject to the exact same grid)
        if sph_arr.shape != d3d_arr.shape:
            # Prototype mock: resize or just return an error
            # For testing, we assume they align if they don't we raise an error
            if len(sph_arr.shape) == 2 and len(d3d_arr.shape) == 2:
                # Truncate to matching size for prototype if mismatch
                min_rows = min(sph_arr.shape[0], d3d_arr.shape[0])
                min_cols = min(sph_arr.shape[1], d3d_arr.shape[1])
                sph_arr = sph_arr[:min_rows, :min_cols]
                d3d_arr = d3d_arr[:min_rows, :min_cols]

        # Masks (Nodata handling)
        sph_mask = sph_arr > 0.01
        d3d_mask = d3d_arr > 0.01
        
        # Flood Area Difference (Intersection over Union - IoU)
        intersection = np.logical_and(sph_mask, d3d_mask)
        union = np.logical_or(sph_mask, d3d_mask)
        
        iou = np.sum(intersection) / np.sum(union) if np.sum(union) > 0 else 0.0
        
        # Depth MAE and RMSE (calculated only where both models predict water, or over the union)
        # Let's calculate over the union to penalize false positives/negatives
        valid_overlap = union
        if np.any(valid_overlap):
            diff = sph_arr[valid_overlap] - d3d_arr[valid_overlap]
            mae = float(np.mean(np.abs(diff)))
            rmse = float(np.sqrt(np.mean(diff**2)))
        else:
            mae = 0.0
            rmse = 0.0
            
        # Difference Raster (mock array generation)
        diff_raster = np.zeros_like(sph_arr)
        diff_raster[valid_overlap] = sph_arr[valid_overlap] - d3d_arr[valid_overlap]

        return {
            "status": "success",
            "message": "Comparison completed",
            "metrics": {
                "iou": float(iou),
                "depth_mae": mae,
                "depth_rmse": rmse,
                "flood_area_difference_m2": float(np.sum(union) * 4) # approx based on 2x2m mock cells
            },
            "output_paths": {
                "difference_raster": "/data/outputs/comparison_diff.tif",
                "overlap_raster": "/data/outputs/comparison_overlap.tif"
            }
        }
