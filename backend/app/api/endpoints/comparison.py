from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from typing import Dict, Any
from pydantic import BaseModel

from app.db.session import get_db_session
from app.models.result import SimulationResult
from app.services.comparison_service import ComparisonService

router = APIRouter()

class ComparisonRequest(BaseModel):
    sph_result_id: uuid.UUID
    delft3d_result_id: uuid.UUID

@router.post("/comparisons")
async def create_comparison(req: ComparisonRequest, db: AsyncSession = Depends(get_db_session)):
    sph_result = await db.get(SimulationResult, req.sph_result_id)
    d3d_result = await db.get(SimulationResult, req.delft3d_result_id)
    
    if not sph_result:
        raise HTTPException(status_code=404, detail="SPH result not found")
        
    # We allow d3d_result to be None, or we pass its data if it exists.
    sph_data = {
        "max_depth_array": sph_result.outputs.get("max_depth_array_mock", [[1.0, 2.0], [0.5, 0.0]]),
        "crs": sph_result.crs,
        "bounds": [0,0,0,0]
    }
    
    if not d3d_result:
        d3d_data = {}
    else:
        d3d_data = {
            "max_depth_array": d3d_result.outputs.get("max_depth_array_mock", [[1.1, 1.9], [0.4, 0.0]]),
            "crs": d3d_result.crs,
            "bounds": [0,0,0,0]
        }
        
    try:
        report = ComparisonService.compare_results(sph_data, d3d_data)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
