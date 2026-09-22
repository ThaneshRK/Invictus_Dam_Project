import zipfile
import pyogrio
from typing import Dict, Any, Optional
from app.core.logger import logger

class DatasetClassifier:
    """
    Analyzes GIS files or ZIP bundles using pyogrio/GDAL (vsizip) to extract 
    metadata (CRS, geometry, fields) and classifies the dataset.
    """
    
    # Classification rules based on expected government fields/geometry
    RULES = {
        "DAM": {
            "geom": ["Point", "MultiPoint"],
            "fields": ["dm_name", "nrld_no", "dm_type", "dam_name", "nrld_id"]
        },
        "RESERVOIR": {
            "geom": ["Polygon", "MultiPolygon"],
            "fields": ["wbname", "area_ha", "reservoir", "res_name"]
        },
        "RIVER_POLYGON": {
            "geom": ["Polygon", "MultiPolygon"],
            "fields": ["rivname", "river", "rivcode"]
        },
        "RIVER": {
            "geom": ["LineString", "MultiLineString", "3D MultiLineString"],
            "fields": ["rivname", "river", "rivcode"]
        }
    }

    def _get_gis_file_in_zip(self, filepath: str) -> Optional[str]:
        """Finds the main GIS file (.shp or .geojson) inside a ZIP archive."""
        try:
            with zipfile.ZipFile(filepath, 'r') as zf:
                namelist = zf.namelist()
                for n in namelist:
                    if n.lower().endswith('.shp') or n.lower().endswith('.geojson') or n.lower().endswith('.gpkg'):
                        # Skip MacOS hidden files
                        if not n.startswith('__MACOSX'):
                            return n
        except Exception as e:
            logger.error(f"Error reading zip {filepath}: {e}")
        return None

    def analyze_dataset(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Reads dataset info and assigns a classification."""
        filepath = metadata["original_path"]
        vsi_path = filepath
        
        if filepath.lower().endswith('.zip'):
            inner_file = self._get_gis_file_in_zip(filepath)
            if inner_file:
                vsi_path = f"/vsizip/{filepath}/{inner_file}"
            else:
                metadata["validation_status"] = "INVALID"
                metadata["classification"] = "UNKNOWN"
                return metadata
                
        try:
            info = pyogrio.read_info(vsi_path)
            
            # CRS might be None if missing
            crs = info.get("crs")
            if crs:
                metadata["crs"] = crs
                
            geom_type = info.get("geometry_type")
            metadata["geometry_type"] = geom_type
            
            fields = list(info.get("fields", []))
            metadata["attribute_names"] = fields
            
            # Calculate total features
            metadata["feature_count"] = info.get("features", 0)
            
            # Bounding box
            bounds = info.get("total_bounds")
            if bounds is not None and len(bounds) == 4:
                metadata["bounding_box"] = list(bounds)
                
            metadata["validation_status"] = "VALID"
            
            # Classification
            metadata["classification"] = self._classify(geom_type, fields)
            
        except Exception as e:
            logger.error(f"Error analyzing GIS dataset {filepath}: {e}")
            metadata["validation_status"] = "INVALID"
            metadata["classification"] = "REVIEW_REQUIRED"
            
        return metadata

    def _classify(self, geom_type: str, fields: list) -> str:
        """Classifies the dataset based on geometry type and fields."""
        if not geom_type:
            return "REVIEW_REQUIRED"
            
        fields_lower = [f.lower() for f in fields]
        
        best_match = "REVIEW_REQUIRED"
        best_score = 0
        
        for classification, rule in self.RULES.items():
            if geom_type not in rule["geom"]:
                continue
                
            # Score based on how many required fields match
            score = sum(1 for rf in rule["fields"] if any(rf in f for f in fields_lower))
            if score > best_score:
                best_score = score
                best_match = classification
                
        if best_score == 0:
            return "REVIEW_REQUIRED"
            
        return best_match
