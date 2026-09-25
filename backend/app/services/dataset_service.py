import os
import shutil
import uuid
import rasterio
import geopandas as gpd
import pandas as pd
from typing import Dict, Any, Tuple
from fastapi import UploadFile, HTTPException

UPLOAD_DIR = "data/projects"

def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

class DatasetService:
    @staticmethod
    async def process_upload(project_id: uuid.UUID, file: UploadFile, dataset_type: str = None) -> Tuple[str, Dict[str, Any]]:
        project_dir = os.path.join(UPLOAD_DIR, str(project_id))
        _ensure_dir(project_dir)
        
        file_path = os.path.join(project_dir, file.filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        metadata = {}
        try:
            if file_ext in ['.tif', '.tiff']:
                metadata = DatasetService._inspect_raster(file_path, dataset_type)
                metadata['format'] = 'GeoTIFF'
            elif file_ext in ['.shp', '.geojson', '.kml']:
                metadata = DatasetService._inspect_vector(file_path, file_ext, dataset_type)
                metadata['format'] = file_ext[1:].upper()
            elif file_ext == '.csv':
                metadata = DatasetService._inspect_csv(file_path, dataset_type)
                metadata['format'] = 'CSV'
            else:
                raise ValueError(f"Unsupported file format: {file_ext}")
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=400, detail=f"Validation failed: {str(e)}")
            
        return file_path, metadata

    @staticmethod
    def _inspect_raster(file_path: str, dataset_type: str = None) -> Dict[str, Any]:
        with rasterio.open(file_path) as src:
            bounds = src.bounds
            
            # Elevation range inspection
            band1 = src.read(1)
            nodata = src.nodata
            if nodata is not None:
                valid_data = band1[band1 != nodata]
                min_val = float(valid_data.min()) if valid_data.size > 0 else 0.0
                max_val = float(valid_data.max()) if valid_data.size > 0 else 0.0
            else:
                min_val = float(band1.min())
                max_val = float(band1.max())
                
            if dataset_type == "DEM" and src.crs is None:
                raise ValueError("DEM must have a valid CRS")

            return {
                "crs": src.crs.to_string() if src.crs else None,
                "bounding_box": f"POLYGON(({bounds.left} {bounds.bottom}, {bounds.right} {bounds.bottom}, {bounds.right} {bounds.top}, {bounds.left} {bounds.top}, {bounds.left} {bounds.bottom}))" if bounds else None,
                "resolution": src.res[0],
                "size": os.path.getsize(file_path) / (1024 * 1024),
                "metadata_": {
                    "count": src.count,
                    "nodata": src.nodata,
                    "dtypes": src.dtypes,
                    "elevation_min": min_val,
                    "elevation_max": max_val
                }
            }

    @staticmethod
    def _inspect_vector(file_path: str, ext: str, dataset_type: str = None) -> Dict[str, Any]:
        if ext == '.kml':
            import fiona
            fiona.drvsupport.supported_drivers['KML'] = 'rw'
            
        gdf = gpd.read_file(file_path)
        if gdf.empty:
            raise ValueError("Vector file is empty")
            
        bounds = gdf.total_bounds
        return {
            "crs": gdf.crs.to_string() if gdf.crs else None,
            "bounding_box": f"POLYGON(({bounds[0]} {bounds[1]}, {bounds[2]} {bounds[1]}, {bounds[2]} {bounds[3]}, {bounds[0]} {bounds[3]}, {bounds[0]} {bounds[1]}))" if bounds is not None else None,
            "resolution": None,
            "size": os.path.getsize(file_path) / (1024 * 1024),
            "metadata_": {
                "features_count": len(gdf),
                "columns": list(gdf.columns.drop('geometry', errors='ignore'))
            }
        }

    @staticmethod
    def _inspect_csv(file_path: str, dataset_type: str = None) -> Dict[str, Any]:
        df = pd.read_csv(file_path)
        if df.empty:
            raise ValueError("CSV file is empty")
            
        if dataset_type == "hydrological":
            required_cols = {'timestamp', 'value'}
            if not required_cols.issubset(set(df.columns)):
                raise ValueError(f"Hydrological CSV must contain at least columns: {required_cols}. Found: {list(df.columns)}")
        
        has_geom = 'latitude' in df.columns and 'longitude' in df.columns
        
        return {
            "crs": "EPSG:4326" if has_geom else None,
            "bounding_box": None,
            "resolution": None,
            "size": os.path.getsize(file_path) / (1024 * 1024),
            "metadata_": {
                "rows": len(df),
                "columns": list(df.columns),
                "has_coordinates": has_geom
            }
        }
