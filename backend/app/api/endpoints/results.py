from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uuid
from typing import List

from app.db.session import get_db_session
from app.models.result import SimulationResult, ResultRead

router = APIRouter()

@router.get("/results/{result_id}", response_model=ResultRead)
async def get_result(result_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    result = await db.get(SimulationResult, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return result

@router.get("/results/{result_id}/metadata")
async def get_result_metadata(result_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    result = await db.get(SimulationResult, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
        
    return {
        "engine": result.engine_used,
        "max_depth_m": result.max_depth_m,
        "inundated_area_km2": result.inundated_area_km2,
        "outputs": result.outputs
    }
