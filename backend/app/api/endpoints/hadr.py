from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uuid
from app.db.session import get_db_session
from app.services.hadr_service import HADRService
from app.models.scenario import Scenario
from app.models.project import Project

router = APIRouter()

class HADRRequest(BaseModel):
    scenario_id: str
    flood_extent_path: str = "/data/mock_extent.geojson"
    exposure_datasets: dict = {}

@router.post("/hadr")
async def calculate_hadr_impact(request: HADRRequest, db: AsyncSession = Depends(get_db_session)):
    """
    Calculates Humanitarian Assistance and Disaster Relief (HADR) impact 
    by intersecting flood extents with exposure datasets.
    """
    try:
        scenario = await db.get(Scenario, uuid.UUID(request.scenario_id))
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
            
        project = await db.get(Project, scenario.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
            
        # Default bounds if none provided (mock 1 degree box around project)
        lat = project.latitude or 11.8 # Mettur Dam approx
        lon = project.longitude or 77.8
        bounds = [lon - 0.5, lat - 0.5, lon + 0.5, lat + 0.5]
        
        results = await HADRService.calculate_exposure(
            flood_extent_path=request.flood_extent_path,
            bounds=bounds,
            scenario_id=request.scenario_id
        )
        return {
            "scenario_id": request.scenario_id,
            "impact": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hadr/{scenario_id}")
async def get_hadr_impact(scenario_id: str, db: AsyncSession = Depends(get_db_session)):
    """
    Endpoint to fetch HADR for a scenario for UI integration.
    """
    scenario = await db.get(Scenario, uuid.UUID(scenario_id))
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
        
    project = await db.get(Project, scenario.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    lat = project.latitude or 11.8
    lon = project.longitude or 77.8
    bounds = [lon - 0.5, lat - 0.5, lon + 0.5, lat + 0.5]
        
    results = await HADRService.calculate_exposure(
        flood_extent_path="/data/mock",
        bounds=bounds,
        scenario_id=scenario_id
    )
    return {
        "scenario_id": scenario_id,
        "impact": results
    }

