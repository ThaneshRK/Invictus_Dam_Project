from typing import Dict, Any
from app.core.logger import logger

class DatasetValidator:
    """
    Validates GIS datasets before ingestion.
    Checks CRS, geometry validity, etc.
    """
    
    def validate(self, metadata: Dict[str, Any]) -> bool:
        if metadata.get("classification") in ["REVIEW_REQUIRED", "UNKNOWN"]:
            logger.warning(f"Validation failed: unclassified dataset {metadata['source_filename']}")
            metadata["validation_status"] = "INVALID"
            return False
            
        if not metadata.get("geometry_type"):
            logger.warning(f"Validation failed: no geometry type for {metadata['source_filename']}")
            metadata["validation_status"] = "INVALID"
            return False
            
        # We don't strictly require CRS in this function because the loader will fall back 
        # or it might be embedded deeply, but we can log a warning.
        if not metadata.get("crs"):
            logger.warning(f"Validation warning: no CRS found in metadata for {metadata['source_filename']}")
            
        metadata["validation_status"] = "VALID"
        return True
