from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from app.services.gee_service import GEEService

router = APIRouter()

class SatelliteExtractionRequest(BaseModel):
    bounds: List[List[float]]
    start_date: str
    end_date: str

@router.post("/satellite/extract")
def extract_flood_extent(request: SatelliteExtractionRequest):
    """
    Triggers an Earth Engine extraction job for Sentinel-1 SAR imagery.
    """
    try:
        result = GEEService.analyze_flood_extent(
            bounds=request.bounds,
            start_date=request.start_date,
            end_date=request.end_date
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
