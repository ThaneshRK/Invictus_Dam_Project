from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.db.session import get_db_session
from app.models.government import GovernmentDataset, GovernmentDam, GovernmentReservoir, GovernmentRiver, DamRelationship
from app.services.government_data.providers_impl import GovernmentStaticHydrologyProvider
from geoalchemy2.shape import from_shape
import shapely.geometry

router = APIRouter()
provider = GovernmentStaticHydrologyProvider()

@router.get("/datasets")
async def get_government_datasets(db: AsyncSession = Depends(get_db_session)):
    """Returns the inventory of all discovered government datasets."""
    result = await db.execute(select(GovernmentDataset))
    datasets = result.scalars().all()
    return {"datasets": datasets}

@router.get("/fixtures")
async def get_government_fixtures():
    """Returns all 5 government-sourced static fixtures for development."""
    systems = provider.get_all_systems()
    return {
        "count": len(systems),
        "source_type": "GOVERNMENT_STATIC_FIXTURE",
        "is_live": False,
        "is_synthetic": False,
        "systems": systems
    }

@router.get("/fixtures/{system_id}")
async def get_government_fixture_by_id(system_id: str):
    """Returns detail for a specific static government fixture."""
    fixture = provider.get_system_fixture(system_id)
    if not fixture:
        raise HTTPException(status_code=404, detail=f"Static fixture for '{system_id}' not found.")
    return fixture

@router.post("/fixtures/seed")
async def seed_government_fixtures(db: AsyncSession = Depends(get_db_session)):
    """Seeds or upserts the 5 static government dam systems into the database."""
    systems = provider.get_all_systems()
    seeded = []

    for sys_data in systems:
        dam_data = sys_data["dam"]
        res_data = sys_data["reservoir"]
        river_data = sys_data["river"]
        
        dam_id = dam_data["id"]
        res_id = res_data["id"]
        river_id = river_data.get("river_id", dam_data.get("river_name", "").lower())
        
        # 1. Upsert Dam
        existing_dam = await db.get(GovernmentDam, dam_id)
        point_geom = from_shape(shapely.geometry.Point(dam_data["longitude"], dam_data["latitude"]), srid=4326)
        
        if existing_dam:
            existing_dam.dam_name = dam_data["dam_name"]
            existing_dam.state = dam_data["state"]
            existing_dam.dam_type = "EMBANKMENT/GRAVITY"
            existing_dam.construction_year = dam_data.get("completion_year")
            existing_dam.source_data = dam_data
            existing_dam.spatial_data_readiness = "AVAILABLE"
            existing_dam.geometry = point_geom
        else:
            new_dam = GovernmentDam(
                id=dam_id,
                dam_name=dam_data["dam_name"],
                state=dam_data["state"],
                district=dam_data.get("district", dam_data["state"]),
                river_code=dam_data["river_name"],
                basin_code=river_data.get("basin", "GENERAL_BASIN"),
                dam_type="EMBANKMENT/GRAVITY",
                construction_year=dam_data.get("completion_year"),
                source_data=dam_data,
                spatial_data_readiness="AVAILABLE",
                geometry=point_geom
            )
            db.add(new_dam)

        # 2. Upsert Reservoir
        existing_res = await db.get(GovernmentReservoir, res_id)
        # Bounding polygon approximation around dam location
        lat, lon = dam_data["latitude"], dam_data["longitude"]
        poly = shapely.geometry.Polygon([
            (lon - 0.05, lat - 0.05),
            (lon + 0.05, lat - 0.05),
            (lon + 0.05, lat + 0.05),
            (lon - 0.05, lat + 0.05),
            (lon - 0.05, lat - 0.05)
        ])
        multi_poly = shapely.geometry.MultiPolygon([poly])
        res_geom = from_shape(multi_poly, srid=4326)

        if existing_res:
            existing_res.name = res_data["reservoir_name"]
            existing_res.source_data = res_data
            existing_res.geometry = res_geom
        else:
            new_res = GovernmentReservoir(
                id=res_id,
                name=res_data["reservoir_name"],
                source_data=res_data,
                geometry=res_geom
            )
            db.add(new_res)

        # 3. Upsert River
        existing_river = await db.get(GovernmentRiver, river_id)
        line = shapely.geometry.LineString([
            (lon - 0.1, lat + 0.1),
            (lon, lat),
            (lon + 0.2, lat - 0.2)
        ])
        multi_line = shapely.geometry.MultiLineString([line])
        river_geom = from_shape(multi_line, srid=4326)

        if existing_river:
            existing_river.name = river_data.get("river_name", dam_data["river_name"])
            existing_river.river_code = river_id
            existing_river.source_data = river_data
            existing_river.geometry = river_geom
        else:
            new_river = GovernmentRiver(
                id=river_id,
                name=river_data.get("river_name", dam_data["river_name"]),
                river_code=river_id,
                source_data=river_data,
                geometry=river_geom
            )
            db.add(new_river)

        # 4. Upsert Relationships
        # Dam -> Reservoir
        rel_res_id = f"rel_{dam_id}_res"
        existing_rel_res = await db.get(DamRelationship, rel_res_id)
        if not existing_rel_res:
            db.add(DamRelationship(
                id=rel_res_id,
                dam_id=dam_id,
                target_type="RESERVOIR",
                target_id=res_id,
                match_method="GOVERNMENT_STATIC_FIXTURE",
                match_distance=0.0,
                match_confidence=1.0,
                match_status="DIRECT"
            ))

        # Dam -> River
        rel_riv_id = f"rel_{dam_id}_riv"
        existing_rel_riv = await db.get(DamRelationship, rel_riv_id)
        if not existing_rel_riv:
            db.add(DamRelationship(
                id=rel_riv_id,
                dam_id=dam_id,
                target_type="RIVER",
                target_id=river_id,
                match_method="GOVERNMENT_STATIC_FIXTURE",
                match_distance=0.0,
                match_confidence=1.0,
                match_status="DIRECT"
            ))

        seeded.append(dam_id)

    await db.commit()
    return {"status": "SUCCESS", "seeded_dams": seeded, "count": len(seeded)}

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
    
    count_query = select(func.count()).select_from(GovernmentDam)
    if state:
        count_query = count_query.where(GovernmentDam.state.ilike(f"%{state}%"))
    if readiness:
        count_query = count_query.where(GovernmentDam.spatial_data_readiness == readiness.upper())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    data = []
    for d in dams:
        data.append({
            "id": d.id,
            "name": d.dam_name,
            "state": d.state,
            "type": d.dam_type,
            "nrld_id": d.nrld_id,
            "readiness": d.spatial_data_readiness,
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
                "target_id": r.target_id,
                "match_method": r.match_method,
                "confidence": r.match_confidence
            } for r in rels
        ]
    }
