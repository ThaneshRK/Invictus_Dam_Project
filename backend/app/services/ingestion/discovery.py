import os
import zipfile
from typing import List, Dict, Any
from app.core.logger import logger
from app.core.config import settings
from app.services.ingestion.registry import DatasetRegistry

class DatasetDiscovery:
    """
    Recursively scans the GOVERNMENT_DATA_DIR to identify geospatial datasets.
    """
    def __init__(self, data_dir: str = settings.GOVERNMENT_DATA_DIR):
        self.data_dir = data_dir

    def scan_directory(self) -> List[Dict[str, Any]]:
        """Recursively finds relevant files and extracts basic metadata."""
        if not os.path.exists(self.data_dir):
            logger.warning(f"Data directory {self.data_dir} does not exist.")
            return []

        discovered = []
        for root, _, files in os.walk(self.data_dir):
            for file in files:
                filepath = os.path.join(root, file)
                ext = file.lower().split('.')[-1]
                
                # We are looking for ZIP, SHP, GeoJSON, KML
                if ext in ['zip', 'geojson', 'shp', 'kml', 'gpkg']:
                    metadata = self._inspect_file(filepath, file, ext)
                    if metadata:
                        discovered.append(metadata)
                        
        return discovered

    def _inspect_file(self, filepath: str, filename: str, ext: str) -> Dict[str, Any]:
        """Inspects a file to determine its format and contents without modifying it."""
        metadata = {
            "original_path": filepath,
            "source_filename": filename,
            "format": ext.upper(),
            "file_size": os.path.getsize(filepath),
            "archive_status": "PENDING" if ext == 'zip' else "EXTRACTED",
            "validation_status": "PENDING",
            "ingestion_status": "PENDING",
            "classification": "REVIEW_REQUIRED" # Will be updated by classifier
        }

        # If it's a zip file, peek inside to see what it contains
        if ext == 'zip':
            try:
                with zipfile.ZipFile(filepath, 'r') as zf:
                    namelist = zf.namelist()
                    # Determine true format inside the zip
                    has_shp = any(n.lower().endswith('.shp') for n in namelist)
                    has_geojson = any(n.lower().endswith('.geojson') for n in namelist)
                    if has_shp:
                        metadata["format"] = "SHP_ZIP"
                    elif has_geojson:
                        metadata["format"] = "GEOJSON_ZIP"
            except zipfile.BadZipFile:
                logger.error(f"Bad zip file: {filepath}")
                metadata["validation_status"] = "INVALID"
        
        return metadata

    async def discover_and_register(self, registry: DatasetRegistry):
        """Runs the discovery process and registers all found datasets."""
        discovered = self.scan_directory()
        registered = []
        for metadata in discovered:
            dataset = await registry.register_dataset(metadata)
            registered.append(dataset)
        return registered
