from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.db.session import get_db_session
from app.models.government import GovernmentDataset, GovernmentDam, DamRelationship

router = APIRouter()

@router.get("/datasets")
async def get_government_datasets(db: AsyncSession = Depends(get_db_session)):
    """Returns the inventory of all discovered government datasets."""
    result = await db.execute(select(GovernmentDataset))
    datasets = result.scalars().all()
    return {"datasets": datasets}

@router.get("/dams")
async def get_government_dams(
    limit: int = Query(50, le=1000),
    offset: int = 0,
    state: Optional[str] = None,
    readiness: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Returns a paginated list of dams, optionally filtered."""
    query = select(GovernmentDam)
    
    if state:
        query = query.where(GovernmentDam.state.ilike(f"%{state}%"))
    if readiness:
        query = query.where(GovernmentDam.spatial_data_readiness == readiness.upper())
        
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    dams = result.scalars().all()
    
    # Get total count
    count_query = select(func.count()).select_from(GovernmentDam)
    if state:
        count_query = count_query.where(GovernmentDam.state.ilike(f"%{state}%"))
    if readiness:
        count_query = count_query.where(GovernmentDam.spatial_data_readiness == readiness.upper())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # We serialize geometry manually or let a Pydantic schema handle it.
    # For now, we return basic info to avoid massive payload.
    data = []
    for d in dams:
        data.append({
            "id": d.id,
            "name": d.dam_name,
            "state": d.state,
            "type": d.dam_type,
            "nrld_id": d.nrld_id,
            "readiness": d.spatial_data_readiness,
            # We skip full geometry for list view, just coords if available
        })
        
    return {"total": total, "dams": data}

@router.get("/dams/{dam_id}")
async def get_government_dam(dam_id: str, db: AsyncSession = Depends(get_db_session)):
    """Returns details for a specific dam."""
    result = await db.execute(select(GovernmentDam).where(GovernmentDam.id == dam_id))
    dam = result.scalars().first()
    if not dam:
        raise HTTPException(status_code=404, detail="Dam not found")
        
    return {
        "id": dam.id,
        "name": dam.dam_name,
        "state": dam.state,
        "district": dam.district,
        "river_code": dam.river_code,
        "basin_code": dam.basin_code,
        "readiness": dam.spatial_data_readiness,
        "source_data": dam.source_data
    }

@router.get("/dams/{dam_id}/readiness")
async def get_dam_readiness(dam_id: str, db: AsyncSession = Depends(get_db_session)):
    """Returns the readiness metrics for a dam."""
    result = await db.execute(select(GovernmentDam).where(GovernmentDam.id == dam_id))
    dam = result.scalars().first()
    if not dam:
        raise HTTPException(status_code=404, detail="Dam not found")
        
    # Find relationships
    rel_result = await db.execute(select(DamRelationship).where(DamRelationship.dam_id == dam_id))
    rels = rel_result.scalars().all()
    
    has_reservoir = any(r.target_type == 'RESERVOIR' for r in rels)
    has_river = any(r.target_type == 'RIVER' for r in rels)
    
    return {
        "dam_id": dam.id,
        "readiness_status": dam.spatial_data_readiness,
        "components": {
            "reservoir": "AVAILABLE" if has_reservoir else "MISSING",
            "river": "AVAILABLE" if has_river else "MISSING"
        },
        "relationships": [
            {
                "target_type": r.target_type,
                "match_method": r.match_method,
                "confidence": r.match_confidence
            } for r in rels
        ]
    }
