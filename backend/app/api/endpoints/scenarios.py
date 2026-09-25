from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uuid
from typing import List

from app.db.session import get_db_session
from app.models.scenario import Scenario
from app.models.project import Project
from app.schemas.scenario import ScenarioCreate, ScenarioRead, ScenarioUpdate
from app.services.scenario_service import ScenarioService

router = APIRouter()

@router.post("/projects/{project_id}/scenarios", response_model=ScenarioRead, status_code=201)
async def create_scenario(project_id: uuid.UUID, scenario_in: ScenarioCreate, db: AsyncSession = Depends(get_db_session)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Strict parameter validation
    valid_params = ScenarioService.validate_parameters(scenario_in.scenario_type, scenario_in.parameters)
    
    scenario = Scenario(
        project_id=project_id,
        name=scenario_in.name,
        scenario_type=scenario_in.scenario_type,
        description=scenario_in.description,
        source_datasets=scenario_in.source_datasets,
        parameters=valid_params,
        simulation_duration=scenario_in.simulation_duration,
        timestep=scenario_in.timestep,
        output_interval=scenario_in.output_interval,
        boundary_conditions=scenario_in.boundary_conditions
    )
    
    db.add(scenario)
    await db.commit()
    await db.refresh(scenario)
    return scenario

@router.get("/projects/{project_id}/scenarios", response_model=List[ScenarioRead])
async def list_scenarios(project_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Scenario).where(Scenario.project_id == project_id))
    return result.scalars().all()

@router.get("/scenarios/{scenario_id}", response_model=ScenarioRead)
async def get_scenario(scenario_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    scenario = await db.get(Scenario, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario

@router.put("/scenarios/{scenario_id}", response_model=ScenarioRead)
async def update_scenario(scenario_id: uuid.UUID, scenario_in: ScenarioUpdate, db: AsyncSession = Depends(get_db_session)):
    scenario = await db.get(Scenario, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
        
    update_data = scenario_in.model_dump(exclude_unset=True)
    
    if "parameters" in update_data:
        update_data["parameters"] = ScenarioService.validate_parameters(scenario.scenario_type, update_data["parameters"])
        
    for field, value in update_data.items():
        setattr(scenario, field, value)
        
    await db.commit()
    await db.refresh(scenario)
    return scenario

@router.delete("/scenarios/{scenario_id}", status_code=204)
async def delete_scenario(scenario_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    scenario = await db.get(Scenario, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
        
    await db.delete(scenario)
    await db.commit()

from app.core.simulation_context import SimulationInputContext

@router.post("/scenarios/{scenario_id}/validate")
async def validate_scenario_configuration(scenario_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    scenario = await db.get(Scenario, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
        
    # Full Phase 1 Validation (DAM -> RESERVOIR -> RIVER -> STUDY AREA -> DEM -> HYDROLOGY)
    ctx = await SimulationInputContext.build(db, scenario.project_id, scenario_id)
    scenario_def = ctx.to_scenario_definition()
        
    config = ScenarioService.serialize_for_engine(scenario)
    
    return {
        "status": "valid",
        "scenario_definition": scenario_def.model_dump(),
        "configuration": config
    }
