import uuid
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException

from app.models.scenario import Scenario, ScenarioType
from app.models.dataset import Dataset, DatasetCategory
from app.schemas.scenario_parameters import DamBreakParameters, WaterReleaseParameters, RiverBlockageParameters

class ScenarioService:
    @staticmethod
    def validate_parameters(scenario_type: ScenarioType, parameters: dict) -> dict:
        """Validates parameters based on the scenario type using Pydantic models."""
        try:
            if scenario_type == ScenarioType.DAM_BREAK:
                return DamBreakParameters(**parameters).model_dump()
            elif scenario_type == ScenarioType.WATER_RELEASE:
                return WaterReleaseParameters(**parameters).model_dump()
            elif scenario_type == ScenarioType.RIVER_BLOCKAGE:
                return RiverBlockageParameters(**parameters).model_dump()
            else:
                raise ValueError(f"Unknown scenario type: {scenario_type}")
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Parameter validation failed: {str(e)}")

    @staticmethod
    async def validate_datasets(db: AsyncSession, project_id: uuid.UUID, dataset_ids: List[uuid.UUID]):
        """Ensures all datasets exist, belong to the project, and check for missing DEMs."""
        if not dataset_ids:
            raise HTTPException(status_code=400, detail="Missing required datasets")
            
        result = await db.execute(
            select(Dataset).where(Dataset.id.in_(dataset_ids), Dataset.project_id == project_id)
        )
        found_datasets = result.scalars().all()
        
        if len(found_datasets) != len(dataset_ids):
            raise HTTPException(status_code=404, detail="One or more datasets not found or do not belong to the project")
            
        has_dem = any(d.dataset_type == DatasetCategory.DEM for d in found_datasets)
        if not has_dem:
            raise HTTPException(status_code=400, detail="A DEM dataset must be provided as a source dataset")
            
        return found_datasets

    @staticmethod
    def serialize_for_engine(scenario: Scenario) -> Dict[str, Any]:
        """Creates a clean, engine-agnostic configuration object for SPH or Delft3D."""
        return {
            "version": "1.0",
            "metadata": {
                "scenario_id": str(scenario.id),
                "name": scenario.name,
                "type": scenario.scenario_type.value,
            },
            "time_control": {
                "duration_hours": scenario.simulation_duration,
                "timestep_seconds": scenario.timestep,
                "output_interval_seconds": scenario.output_interval
            },
            "physics_parameters": scenario.parameters,
            "boundary_conditions": scenario.boundary_conditions or {},
            "inputs": {
                "datasets": [str(d) for d in (scenario.source_datasets or [])]
            }
        }
