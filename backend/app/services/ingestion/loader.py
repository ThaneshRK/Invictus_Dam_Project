import os
import subprocess
import uuid
import zipfile
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.logger import logger
from app.core.config import settings
from app.models.government import GovernmentDataset

class PostGISLoader:
    """
    Handles robust bulk loading of datasets into PostGIS using ogr2ogr.
    It stages data in a temporary table, then normalizes and inserts it 
    into the designated model table.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.pg_conn_str = f"PG:host={settings.POSTGRES_SERVER} port={settings.POSTGRES_PORT} dbname={settings.POSTGRES_DB} user={settings.POSTGRES_USER} password={settings.POSTGRES_PASSWORD}"

    def _get_gis_file_in_zip(self, filepath: str) -> Optional[str]:
        try:
            with zipfile.ZipFile(filepath, 'r') as zf:
                for n in zf.namelist():
                    if n.lower().endswith('.shp') or n.lower().endswith('.geojson') or n.lower().endswith('.gpkg'):
                        if not n.startswith('__MACOSX'):
                            return n
        except:
            pass
        return None

    async def load_dataset(self, dataset: GovernmentDataset) -> bool:
        if dataset.classification == "REVIEW_REQUIRED" or dataset.classification == "UNKNOWN":
            logger.warning(f"Cannot load unclassified dataset: {dataset.source_filename}")
            return False
            
        temp_table = f"temp_load_{uuid.uuid4().hex[:8]}"
        filepath = dataset.original_path
        vsi_path = filepath
        
        if filepath.lower().endswith('.zip'):
            inner_file = self._get_gis_file_in_zip(filepath)
            if inner_file:
                vsi_path = f"/vsizip/{filepath}/{inner_file}"
            else:
                return False

        # Run ogr2ogr to load into temporary table
        # We transform to EPSG:4326 for standard unified storage, 
        # while keeping original CRS metadata in the Dataset record.
        cmd = [
            "ogr2ogr",
            "-f", "PostgreSQL",
            self.pg_conn_str,
            vsi_path,
            "-nln", temp_table,
            "-nlt", "PROMOTE_TO_MULTI",
            "-t_srs", "EPSG:4326",
            "-lco", "GEOMETRY_NAME=geometry",
            "-lco", "PRECISION=NO",
            "-overwrite"
        ]
        
        logger.info(f"Running ogr2ogr for {dataset.source_filename} into {temp_table}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"ogr2ogr failed: {e.stderr}")
            return False

        # Normalize and insert into target tables
        success = await self._normalize_and_insert(dataset, temp_table)
        
        # Cleanup
        try:
            await self.db.execute(text(f"DROP TABLE IF EXISTS {temp_table} CASCADE"))
            await self.db.commit()
        except Exception as e:
            logger.error(f"Failed to drop temp table {temp_table}: {e}")
            
        return success

    async def _normalize_and_insert(self, dataset: GovernmentDataset, temp_table: str) -> bool:
        """Transfers data from temp_table to normalized government tables."""
        
        target_table = None
        sql = ""
        
        if dataset.classification == "DAM":
            target_table = "government_dams"
            # Map fields safely. We use COALESCE to handle varying case schemas
            sql = f"""
            INSERT INTO {target_table} (id, dataset_id, dam_name, source_id, nrld_id, state, river_code, basin_code, dam_type, geometry, source_data, spatial_data_readiness)
            SELECT 
                gen_random_uuid()::varchar,
                '{dataset.id}',
                COALESCE((SELECT value FROM jsonb_each_text(row_to_json(t)::jsonb) WHERE key ILIKE '%dm_name%' OR key ILIKE '%dam_name%' LIMIT 1), 'Unknown Dam'),
                COALESCE((SELECT value FROM jsonb_each_text(row_to_json(t)::jsonb) WHERE key ILIKE '%strucode%' LIMIT 1), NULL),
                COALESCE((SELECT value FROM jsonb_each_text(row_to_json(t)::jsonb) WHERE key ILIKE '%nrld%' LIMIT 1), NULL),
                COALESCE((SELECT value FROM jsonb_each_text(row_to_json(t)::jsonb) WHERE key ILIKE 'state' LIMIT 1), NULL),
                COALESCE((SELECT value FROM jsonb_each_text(row_to_json(t)::jsonb) WHERE key ILIKE 'rivcode' LIMIT 1), NULL),
                COALESCE((SELECT value FROM jsonb_each_text(row_to_json(t)::jsonb) WHERE key ILIKE 'bacode' LIMIT 1), NULL),
                COALESCE((SELECT value FROM jsonb_each_text(row_to_json(t)::jsonb) WHERE key ILIKE 'dm_type' LIMIT 1), NULL),
                ST_Centroid(ST_Transform(geometry, 4326)),
                row_to_json(t)::jsonb,
                'REVIEW_REQUIRED'
            FROM {temp_table} t
            WHERE geometry IS NOT NULL;
            """
            
        elif dataset.classification == "RESERVOIR":
            target_table = "government_reservoirs"
            sql = f"""
            INSERT INTO {target_table} (id, dataset_id, source_id, name, geometry, source_data)
            SELECT 
                gen_random_uuid()::varchar,
                '{dataset.id}',
                COALESCE((SELECT value FROM jsonb_each_text(row_to_json(t)::jsonb) WHERE key ILIKE 'wbcode' LIMIT 1), NULL),
                COALESCE((SELECT value FROM jsonb_each_text(row_to_json(t)::jsonb) WHERE key ILIKE 'wbname' OR key ILIKE '%res_name%' LIMIT 1), 'Unknown Reservoir'),
                ST_Multi(ST_Transform(geometry, 4326)),
                row_to_json(t)::jsonb
            FROM {temp_table} t
            WHERE geometry IS NOT NULL;
            """
            
        elif dataset.classification == "RIVER":
            target_table = "government_rivers"
            sql = f"""
            INSERT INTO {target_table} (id, dataset_id, source_id, name, river_code, geometry, source_data)
            SELECT 
                gen_random_uuid()::varchar,
                '{dataset.id}',
                COALESCE((SELECT value FROM jsonb_each_text(row_to_json(t)::jsonb) WHERE key ILIKE 'objectid' LIMIT 1), NULL),
                COALESCE((SELECT value FROM jsonb_each_text(row_to_json(t)::jsonb) WHERE key ILIKE 'rivname' OR key ILIKE 'river' LIMIT 1), 'Unknown River'),
                COALESCE((SELECT value FROM jsonb_each_text(row_to_json(t)::jsonb) WHERE key ILIKE 'rivcode' LIMIT 1), NULL),
                ST_Multi(ST_Transform(geometry, 4326)),
                row_to_json(t)::jsonb
            FROM {temp_table} t
            WHERE geometry IS NOT NULL;
            """
            
        elif dataset.classification == "RIVER_POLYGON":
            target_table = "government_river_polygons"
            sql = f"""
            INSERT INTO {target_table} (id, dataset_id, source_id, name, geometry, source_data)
            SELECT 
                gen_random_uuid()::varchar,
                '{dataset.id}',
                COALESCE((SELECT value FROM jsonb_each_text(row_to_json(t)::jsonb) WHERE key ILIKE 'objectid' LIMIT 1), NULL),
                COALESCE((SELECT value FROM jsonb_each_text(row_to_json(t)::jsonb) WHERE key ILIKE 'rivname' OR key ILIKE 'river' LIMIT 1), 'Unknown River Polygon'),
                ST_Multi(ST_Transform(geometry, 4326)),
                row_to_json(t)::jsonb
            FROM {temp_table} t
            WHERE geometry IS NOT NULL;
            """
            
        if sql:
            try:
                await self.db.execute(text(sql))
                await self.db.commit()
                logger.info(f"Successfully loaded data into {target_table}")
                return True
            except Exception as e:
                logger.error(f"Error transferring data to {target_table}: {e}")
                await self.db.rollback()
                return False
        
        return False
