from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import asyncio
from datetime import datetime, timezone
from typing import List

from app.db.session import get_db_session, async_session_factory
from app.models.job import SimulationJob, JobStatus
from app.models.project import Project
from app.models.scenario import Scenario
from app.schemas.job import SimulationJobCreate, SimulationJobRead, JobStatusResponse
from app.engines.sph.engine import SPHEngine
from app.engines.delft3d.engine import Delft3DEngine
from app.core.simulation_context import SimulationInputContext
from app.services.inundation_service import InundationService

router = APIRouter()

# Memory registry for cancellation of local processes
active_jobs = {}

async def run_simulation_task(job_id: uuid.UUID):
    async with async_session_factory() as db:
        job = await db.get(SimulationJob, job_id)
        if not job:
            return
            
        result = await db.execute(select(Scenario).where(Scenario.id == job.scenario_id))
        scenario = result.scalar_one_or_none()
        if not scenario:
            return
        
        job.status = JobStatus.VALIDATING
        job.start_time = datetime.now(timezone.utc)
        await db.commit()
        
        try:
            # 1. Build authoritative Physical Context
            context = await SimulationInputContext.build(db, job.project_id, job.scenario_id)
        except HTTPException as e:
            job.status = JobStatus.VALIDATION_FAILED
            job.error = f"Validation failed: {e.detail}"
            await db.commit()
            return
            
        # 2. Record Input Snapshot
        job.input_snapshot = {
            "dem_id": str(context.dem.id) if context.dem else None,
            "hydrology_id": str(context.hydrology.id) if context.hydrology else None,
            "dam_id": str(context.dam.id),
            "reservoir_id": str(context.reservoir.id),
            "river_id": str(context.river.id),
            "scenario_type": context.scenario.scenario_type.value if hasattr(context.scenario.scenario_type, 'value') else str(context.scenario.scenario_type),
            "scenario_parameters": context.scenario.parameters or {}
        }
        job.status = JobStatus.VALIDATED
        await db.commit()
        
        # 3. Instantiate correct engine Adapter
        job.status = JobStatus.PREPARING
        await db.commit()
        
        engine_name = job.engine.upper()
        
        if engine_name in ("SPH", "SPH2D"):
            engine = SPHEngine(context)
        elif engine_name == "SPH3D":
            engine = SPHEngine(context, use_3d=True)
        elif engine_name == "DELFT3D":
            engine = Delft3DEngine(context)
        else:
            job.status = JobStatus.PREPARATION_FAILED
            job.error = f"Unknown Engine: {job.engine}. Valid engines: SPH, SPH2D, SPH3D, DELFT3D"
            await db.commit()
            return

        active_jobs[job.id] = engine

        # Prepare
        valid = engine.validate()
        if not valid:
            job.status = JobStatus.PREPARATION_FAILED
            job.error = engine.error_message or "Engine Validation failed"
            await db.commit()
            return
            
        engine.prepare()
        if engine.status == "FAILED":
            job.status = JobStatus.PREPARATION_FAILED
            job.error = engine.error_message
            await db.commit()
            return
            
        job.status = JobStatus.RUNNING
        await db.commit()

        # Run in executor while updating live DB progress
        loop = asyncio.get_event_loop()
        run_task = loop.run_in_executor(None, engine.run)

        while not run_task.done():
            await asyncio.sleep(0.5)
            if job.id in active_jobs:
                eng_stat = active_jobs[job.id].get_status()
                if isinstance(eng_stat.get("progress_percent"), (int, float)):
                    job.progress = float(eng_stat["progress_percent"])
                    await db.commit()

        await run_task
        
        if engine.status == "CANCELLED":
            job.status = JobStatus.CANCELLED
            job.end_time = datetime.now(timezone.utc)
            await db.commit()
            return
            
        if engine.status == "FAILED":
            job.status = JobStatus.EXECUTION_FAILED
            job.error = engine.error_message
            await db.commit()
            return
            
        job.status = JobStatus.PARSING
        await db.commit()
        
        # Post process results
        try:
            raw_results = engine.load_results()
            if not raw_results:
                raise ValueError("Engine completed but no results were loaded.")
            
            job.status = JobStatus.VALIDATING_OUTPUT
            await db.commit()
            
            max_depth_val = raw_results.get("max_water_depth")
            if max_depth_val is None and "max_depth_array" in raw_results:
                arr = [x for row in raw_results["max_depth_array"] for x in row if x is not None]
                max_depth_val = max(arr) if arr else 1.0
            if max_depth_val is None:
                max_depth_val = 1.0
                
            if max_depth_val <= 0:
                raise ValueError("Physical validation failed: Maximum water depth is <= 0")
                
            processed = InundationService.process_engine_output(raw_results)
            result_record = await InundationService.create_result_record(
                db, job.project_id, job.scenario_id, job.engine, "EPSG:4326", processed
            )
            job.result_references = {"result_id": str(result_record.id)}
            
            job.status = JobStatus.COMPLETED
            job.progress = 100.0
            
        except Exception as e:
            job.status = JobStatus.OUTPUT_FAILED
            job.error = f"Output Parsing/Validation failed: {str(e)}"

        job.end_time = datetime.now(timezone.utc)
        await db.commit()
        
        active_jobs.pop(job.id, None)


@router.post("/simulations", response_model=SimulationJobRead, status_code=202)
async def create_simulation(
    req: SimulationJobCreate, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    job = SimulationJob(
        project_id=req.project_id,
        scenario_id=req.scenario_id,
        engine=req.engine,
        operation=req.operation,
        status=JobStatus.CREATED
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    background_tasks.add_task(run_simulation_task, job.id)
    return job

@router.get("/simulations", response_model=List[SimulationJobRead])
async def list_all_simulations(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(SimulationJob).order_by(SimulationJob.created_at.desc()))
    jobs = result.scalars().all()
    jobs_out = []
    for job in jobs:
        job_read = SimulationJobRead.model_validate(job) if hasattr(SimulationJobRead, 'model_validate') else SimulationJobRead.from_orm(job)
        if job_read.status == JobStatus.RUNNING and job_read.id in active_jobs:
            eng_stat = active_jobs[job_read.id].get_status()
            if isinstance(eng_stat.get("progress_percent"), (int, float)):
                job_read.progress = float(eng_stat["progress_percent"])
        jobs_out.append(job_read)
    return jobs_out

@router.get("/projects/{project_id}/simulations", response_model=List[SimulationJobRead])
async def list_project_simulations(project_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(SimulationJob).where(SimulationJob.project_id == project_id).order_by(SimulationJob.created_at.desc()))
    jobs = result.scalars().all()
    
    jobs_out = []
    # Inject live progress for running jobs
    for job in jobs:
        job_read = SimulationJobRead.model_validate(job) if hasattr(SimulationJobRead, 'model_validate') else SimulationJobRead.from_orm(job)
        if job_read.status == JobStatus.RUNNING and job_read.id in active_jobs:
            eng_stat = active_jobs[job_read.id].get_status()
            if isinstance(eng_stat.get("progress_percent"), (int, float)):
                job_read.progress = float(eng_stat["progress_percent"])
        jobs_out.append(job_read)
                
    return jobs_out

@router.get("/simulations/{job_id}", response_model=SimulationJobRead)
async def get_simulation(job_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    job = await db.get(SimulationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job_read = SimulationJobRead.model_validate(job) if hasattr(SimulationJobRead, 'model_validate') else SimulationJobRead.from_orm(job)
    if job_read.status == JobStatus.RUNNING and job_read.id in active_jobs:
        eng_stat = active_jobs[job_read.id].get_status()
        if isinstance(eng_stat.get("progress_percent"), (int, float)):
            job_read.progress = float(eng_stat["progress_percent"])
    return job_read

@router.get("/simulations/{job_id}/status", response_model=JobStatusResponse)
async def get_simulation_status(job_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    job = await db.get(SimulationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    engine_progress = 0.0
    if job.id in active_jobs:
        eng_stat = active_jobs[job.id].get_status()
        if isinstance(eng_stat.get("progress_percent"), (int, float)):
            engine_progress = float(eng_stat["progress_percent"])
            
    return JobStatusResponse(
        status=job.status,
        progress=engine_progress if job.status == JobStatus.RUNNING else job.progress,
        error=job.error
    )

@router.get("/simulations/{job_id}/logs")
async def get_simulation_logs(job_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    job = await db.get(SimulationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"logs": job.logs or "No logs available"}

@router.post("/simulations/{job_id}/cancel")
async def cancel_simulation(job_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    job = await db.get(SimulationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="Cannot cancel a finished job")
        
    if job.id in active_jobs:
        active_jobs[job.id].cancel()
        
    job.status = JobStatus.CANCELLED
    await db.commit()
    return {"status": "CANCELLED"}
