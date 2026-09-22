import asyncio
import os
import sys

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.logger import logger
from app.services.ingestion.discovery import DatasetDiscovery
from app.services.ingestion.registry import DatasetRegistry
from app.services.ingestion.classification import DatasetClassifier
from app.services.ingestion.validation import DatasetValidator
from app.services.ingestion.loader import PostGISLoader
from app.services.ingestion.relationships import RelationshipDiscovery
from app.services.ingestion.readiness import ReadinessCalculator

async def run_ingestion():
    engine = create_async_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        registry = DatasetRegistry(db)
        discovery = DatasetDiscovery()
        classifier = DatasetClassifier()
        validator = DatasetValidator()
        loader = PostGISLoader(db)
        
        logger.info("=== PHASE 1: DISCOVERY & REGISTRY ===")
        registered_datasets = await discovery.discover_and_register(registry)
        
        logger.info(f"Discovered {len(registered_datasets)} datasets.")
        
        for ds in registered_datasets:
            logger.info(f"=== PROCESSING DATASET: {ds.source_filename} ===")
            
            # Convert model to dict for processing
            metadata = {
                "original_path": ds.original_path,
                "source_filename": ds.source_filename,
                "format": ds.format,
                "classification": ds.classification,
                "validation_status": ds.validation_status
            }
            
            ds_id = ds.id
            ds_original_path = ds.original_path
            # Classification
            metadata = classifier.analyze_dataset(metadata)
            await registry.update_status(ds_id, "classification", metadata["classification"])
            await registry.update_status(ds_id, "crs", metadata.get("crs"))
            await registry.update_status(ds_id, "geometry_type", metadata.get("geometry_type"))
            await registry.update_status(ds_id, "feature_count", metadata.get("feature_count"))
            
            # Validation
            if validator.validate(metadata):
                await registry.update_status(ds_id, "validation_status", "VALID")
                
                # Ingestion
                logger.info(f"Loading {ds.source_filename} into PostGIS...")
                
                # Refresh ds from db
                current_ds = await registry.get_dataset_by_path(ds_original_path)
                success = await loader.load_dataset(current_ds)
                
                if success:
                    await registry.update_status(ds_id, "ingestion_status", "INGESTED")
                else:
                    await registry.update_status(ds_id, "ingestion_status", "ERROR")
            else:
                await registry.update_status(ds_id, "validation_status", "INVALID")
                await registry.update_status(ds_id, "ingestion_status", "SKIPPED")
                
        # Phase 8 & 10: Relationships & Readiness
        logger.info("=== PHASE 8: RELATIONSHIPS ===")
        rel_discovery = RelationshipDiscovery(db)
        await rel_discovery.run_discovery()
        
        logger.info("=== PHASE 10: READINESS ===")
        readiness = ReadinessCalculator(db)
        await readiness.update_all_dams()
        
        logger.info("=== INGESTION PIPELINE COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(run_ingestion())
