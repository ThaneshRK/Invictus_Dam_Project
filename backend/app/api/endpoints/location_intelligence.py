from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uuid
from typing import Dict, Any, List

from app.db.session import get_db_session
from app.models.location_intelligence import (
    LocationEnrichmentJob, ProjectDamCandidate, ProjectDam,
    PopulationSnapshot, WaterSnapshot
)

router = APIRouter()

@router.get("/{project_id}/enrichment")
async def get_location_intelligence(project_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    """
    Fetch all location intelligence data for a project.
    """
    # 1. Check Job Status
    job_res = await db.execute(select(LocationEnrichmentJob).filter_by(project_id=project_id).order_by(LocationEnrichmentJob.created_at.desc()))
    job = job_res.scalars().first()
    
    # 2. Dam Candidate
    cand_res = await db.execute(select(ProjectDamCandidate).filter_by(project_id=project_id))
    candidates = cand_res.scalars().all()
    
    # 3. Selected Dam
    dam_res = await db.execute(select(ProjectDam).filter_by(project_id=project_id))
    dam = dam_res.scalars().first()
    
    # 4. Population
    pop_res = await db.execute(select(PopulationSnapshot).filter_by(project_id=project_id))
    population = pop_res.scalars().first()
    
    # 5. Water
    water_res = await db.execute(select(WaterSnapshot).filter_by(project_id=project_id))
    water = water_res.scalars().first()
    
    return {
        "job_status": job.status if job else "NONE",
        "provider_status": job.provider_status if job else {},
        "candidates": candidates,
        "selected_dam": dam,
        "population": population,
        "water_snapshot": water
    }
