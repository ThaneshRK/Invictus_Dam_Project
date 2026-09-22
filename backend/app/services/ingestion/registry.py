import os
import zipfile
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.government import GovernmentDataset
from app.core.logger import logger

class DatasetRegistry:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_datasets(self) -> List[GovernmentDataset]:
        result = await self.db.execute(select(GovernmentDataset))
        return result.scalars().all()

    async def get_dataset_by_path(self, path: str) -> Optional[GovernmentDataset]:
        result = await self.db.execute(
            select(GovernmentDataset).where(GovernmentDataset.original_path == path)
        )
        return result.scalars().first()

    async def register_dataset(self, metadata: Dict[str, Any]) -> GovernmentDataset:
        """Registers a new dataset or updates an existing one."""
        existing = await self.get_dataset_by_path(metadata["original_path"])
        if existing:
            # Update existing
            for key, value in metadata.items():
                setattr(existing, key, value)
            existing.updated_at = existing.updated_at # Trigger update
            dataset = existing
            logger.info(f"Updated registry entry for {metadata['original_path']}")
        else:
            # Create new
            dataset = GovernmentDataset(**metadata)
            self.db.add(dataset)
            logger.info(f"Registered new dataset: {metadata['original_path']}")
            
        await self.db.commit()
        await self.db.refresh(dataset)
        return dataset

    async def update_status(self, dataset_id: str, field: str, value: str):
        """Update a specific status field of a dataset."""
        result = await self.db.execute(
            select(GovernmentDataset).where(GovernmentDataset.id == dataset_id)
        )
        dataset = result.scalars().first()
        if dataset:
            setattr(dataset, field, value)
            await self.db.commit()
            await self.db.refresh(dataset)
            return dataset
        return None
