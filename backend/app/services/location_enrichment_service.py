import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone
from app.db.session import async_session_factory
from app.models.project import Project
from app.models.location_intelligence import (
    LocationEnrichmentJob, ProjectLocation, ProjectDamCandidate, 
    ProjectDam, PopulationSnapshot, WaterSnapshot
)
from app.services.government_data.registry import (
    get_dam_provider, get_population_provider, get_water_provider
)

logger = logging.getLogger(__name__)

async def run_enrichment_job(project_id: uuid.UUID, job_id: uuid.UUID):
    """
    Background job to enrich project location with government data.
    """
    async with async_session_factory() as db:
        job = await db.get(LocationEnrichmentJob, job_id)
        if not job:
            return
            
        project = await db.get(Project, project_id)
        if not project or project.latitude is None or project.longitude is None:
            job.status = "FAILED"
            job.provider_status = {"error": "Project has no coordinates"}
            await db.commit()
            return
            
        lat, lon = project.latitude, project.longitude
        
        job.status = "RUNNING"
        provider_status = {}
        await db.commit()
        
        dam_provider = get_dam_provider()
        pop_provider = get_population_provider()
        water_provider = get_water_provider()
        
        # 1. Store Project Location
        loc_result = await db.execute(select(ProjectLocation).filter_by(project_id=project_id))
        loc = loc_result.scalars().first()
        if not loc:
            loc = ProjectLocation(
                project_id=project_id,
                latitude=lat,
                longitude=lon,
                location_geometry=f"SRID=4326;POINT({lon} {lat})"
            )
            db.add(loc)
            await db.commit()
            
        has_errors = False

        # 2. Find nearby dams
        try:
            nearby_dams = await dam_provider.find_nearby_dams(lat, lon, radius_km=50.0)
            
            # Clear old candidates
            old_candidates = await db.execute(select(ProjectDamCandidate).filter_by(project_id=project_id))
            for old_c in old_candidates.scalars().all():
                await db.delete(old_c)
                
            for d in nearby_dams:
                cand = ProjectDamCandidate(
                    project_id=project_id,
                    dam_name=d.get("dam_name"),
                    distance_km=d.get("distance_km"),
                    source_name=d.get("source_name"),
                    source_record_id=d.get("source_record_id"),
                    metadata_json=d.get("metadata")
                )
                db.add(cand)
                
            # If we found at least one dam, automatically select the closest one and fetch details
            if nearby_dams:
                closest = nearby_dams[0]
                dam_details_res = await dam_provider.get_dam_details(closest["source_record_id"])
                
                if "data" in dam_details_res:
                    data = dam_details_res["data"]
                    
                    old_dam_res = await db.execute(select(ProjectDam).filter_by(project_id=project_id))
                    old_dam = old_dam_res.scalars().first()
                    if old_dam:
                        await db.delete(old_dam)
                        
                    pd = ProjectDam(
                        project_id=project_id,
                        dam_name=data.get("dam_name"),
                        project_identification_code=data.get("project_identification_code"),
                        operator=data.get("operator"),
                        year_completed=data.get("year_completed"),
                        river_basin=data.get("river_basin"),
                        river=data.get("river"),
                        nearest_city=data.get("nearest_city"),
                        seismic_zone=data.get("seismic_zone"),
                        dam_type=data.get("dam_type"),
                        dam_height_m=data.get("dam_height_m"),
                        dam_length_m=data.get("dam_length_m"),
                        gross_storage_capacity_mcm=data.get("gross_storage_capacity_mcm"),
                        reservoir_area_sq_km=data.get("reservoir_area_sq_km"),
                        effective_storage_capacity_mcm=data.get("effective_storage_capacity_mcm"),
                        purpose=data.get("purpose"),
                        designed_spillway_capacity_cumec=data.get("designed_spillway_capacity_cumec"),
                        source_name=dam_details_res.get("source_name"),
                        source_url=dam_details_res.get("source_url"),
                        source_record_id=dam_details_res.get("source_record_id"),
                        retrieved_at=datetime.fromisoformat(dam_details_res.get("retrieved_at"))
                    )
                    db.add(pd)
                    
                    # 2.5 Fetch water data for this dam
                    try:
                        water_res = await water_provider.get_water_information(pd.project_identification_code, lat, lon)
                        if "data" in water_res:
                            wdata = water_res["data"]
                            old_w_res = await db.execute(select(WaterSnapshot).filter_by(project_id=project_id))
                            old_w = old_w_res.scalars().first()
                            if old_w:
                                await db.delete(old_w)
                                
                            ws = WaterSnapshot(
                                project_id=project_id,
                                current_water_level_m=wdata.get("current_water_level_m"),
                                live_storage_mcm=wdata.get("live_storage_mcm"),
                                storage_percentage=wdata.get("storage_percentage"),
                                inflow_cumec=wdata.get("inflow_cumec"),
                                outflow_cumec=wdata.get("outflow_cumec"),
                                observation_date=datetime.fromisoformat(water_res.get("observation_date")),
                                source_name=water_res.get("source_name"),
                                retrieved_at=datetime.fromisoformat(water_res.get("retrieved_at"))
                            )
                            db.add(ws)
                            provider_status["water"] = "SUCCESS"
                        else:
                            provider_status["water"] = "UNAVAILABLE"
                    except Exception as e:
                        logger.error(f"Water provider error: {e}")
                        provider_status["water"] = "FAILED"
                        has_errors = True
                
            provider_status["dam"] = "SUCCESS"
        except Exception as e:
            logger.error(f"Dam provider error: {e}")
            provider_status["dam"] = "FAILED"
            has_errors = True

        # 3. Fetch population
        try:
            pop_res = await pop_provider.get_population(lat, lon, radii_km=[5, 10, 25])
            if "data" in pop_res:
                pdata = pop_res["data"]
                
                old_p_res = await db.execute(select(PopulationSnapshot).filter_by(project_id=project_id))
                old_p = old_p_res.scalars().first()
                if old_p:
                    await db.delete(old_p)
                    
                ps = PopulationSnapshot(
                    project_id=project_id,
                    population_5km=pdata.get("population_5km"),
                    population_10km=pdata.get("population_10km"),
                    population_25km=pdata.get("population_25km"),
                    source_name=pop_res.get("source_name"),
                    reference_year=pop_res.get("reference_year"),
                    methodology=pop_res.get("methodology"),
                    retrieved_at=datetime.fromisoformat(pop_res.get("retrieved_at"))
                )
                db.add(ps)
                provider_status["population"] = "SUCCESS"
            else:
                provider_status["population"] = "UNAVAILABLE"
        except Exception as e:
            logger.error(f"Population provider error: {e}")
            provider_status["population"] = "FAILED"
            has_errors = True
            
        # Update job
        job.provider_status = provider_status
        job.status = "PARTIAL" if has_errors else "COMPLETED"
        await db.commit()
