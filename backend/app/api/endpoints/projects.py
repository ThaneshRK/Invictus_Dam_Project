import uuid
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete

from app.db.session import get_db_session
from app.models.project import Project
from app.models.scenario import Scenario, InitialCondition, DamBreakParameters, ControlledReleaseParameters, RiverBlockageParameters
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.government_data.registry import get_dam_provider

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=ProjectRead, status_code=201)
@router.post("", response_model=ProjectRead, status_code=201, include_in_schema=False)
async def create_project(project_in: ProjectCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db_session)):
    project = Project(
        name=project_in.name,
        description=project_in.description,
        latitude=project_in.latitude,
        longitude=project_in.longitude,
        crs=project_in.crs,
        project_type=project_in.project_type if hasattr(project_in, "project_type") else "General Flood Study",
        study_area=None
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    # Create enrichment job
    from app.models.location_intelligence import LocationEnrichmentJob
    from app.services.location_enrichment_service import run_enrichment_job
    
    job = LocationEnrichmentJob(project_id=project.id, status="PENDING")
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Trigger background task
    background_tasks.add_task(run_enrichment_job, project.id, job.id)
    
    return project

@router.get("/", response_model=List[ProjectRead])
@router.get("", response_model=List[ProjectRead], include_in_schema=False)
async def read_projects(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Project).offset(skip).limit(limit))
    return result.scalars().all()

@router.get("/{project_id}", response_model=ProjectRead)
async def read_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.put("/{project_id}", response_model=ProjectRead)
async def update_project(project_id: uuid.UUID, project_in: ProjectUpdate, db: AsyncSession = Depends(get_db_session)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    update_data = project_in.model_dump(exclude_unset=True)
    
    # Handle study_area GeoJSON → PostGIS geometry conversion
    if 'study_area' in update_data and update_data['study_area'] is not None:
        from shapely.geometry import shape
        from geoalchemy2.shape import from_shape
        try:
            geom = shape(update_data['study_area'])
            update_data['study_area'] = from_shape(geom, srid=4326)
        except Exception as e:
            logger.error(f"Failed to convert study_area GeoJSON: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid study area geometry: {str(e)}")
    
    for field, value in update_data.items():
        setattr(project, field, value)
        
    await db.commit()
    await db.refresh(project)
    return project

@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)
    await db.commit()

# --- Wizard Endpoints ---

@router.get("/{project_id}/nearby-dams")
async def get_nearby_dams(
    project_id: uuid.UUID, 
    latitude: float = Query(...), 
    longitude: float = Query(...), 
    radius_km: float = Query(50.0),
    db: AsyncSession = Depends(get_db_session)
):
    provider = get_dam_provider()
    try:
        dams = await provider.find_nearby_dams(latitude, longitude, radius_km)
        return {"dams": dams}
    except Exception as e:
        logger.error(f"Error finding dams: {e}")
        return {"dams": []}

@router.get("/{project_id}/data-readiness")
async def get_data_readiness(project_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    readiness = {
        "location": bool(project.latitude and project.longitude),
        "dam": bool(project.selected_dam_id),
        "reservoir": bool(project.selected_reservoir_id),
        "study_area": bool(getattr(project, "study_area", None)),
        "dem": bool(project.dem_dataset_id),
    }
    
    completed = sum(1 for v in readiness.values() if v)
    total = len(readiness)
    
    return {
        "readiness": readiness,
        "score_percentage": int((completed / total) * 100) if total > 0 else 0
    }

@router.post("/{project_id}/finalize")
async def finalize_project(project_id: uuid.UUID, payload: Dict[str, Any], db: AsyncSession = Depends(get_db_session)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Normally we would validate `payload` deeply here and create the Scenario and Parameters tables.
    
    scenario = Scenario(
        project_id=project.id,
        name=f"Scenario for {project.name}",
        scenario_type=project.project_type or "DAM_BREAK",
        simulation_duration=24.0,
        timestep=1.0,
        output_interval=3600.0
    )
    db.add(scenario)
    await db.commit()
    await db.refresh(scenario)
    
    # Store parameters if provided
    params = payload.get("scenario_params", {})
    
    initial_condition = InitialCondition(
        scenario_id=scenario.id,
        water_level=float(params.get("initial_water_level", 0)) if params.get("initial_water_level") else None
    )
    db.add(initial_condition)
    
    if scenario.scenario_type == "Dam Break Flood":
        db_params = DamBreakParameters(
            scenario_id=scenario.id,
            breach_width=float(params.get("breach_width", 0)) if params.get("breach_width") else None,
            formation_time=float(params.get("formation_time", 0)) if params.get("formation_time") else None,
            failure_time=0.0
        )
        db.add(db_params)
    
    # Update project with success
    project.data_readiness_status = 100.0
    await db.commit()
    
    return {"status": "SUCCESS", "scenario_id": str(scenario.id)}
