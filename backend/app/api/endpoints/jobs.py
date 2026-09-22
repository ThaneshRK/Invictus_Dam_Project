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
        
        # Load relationships explicitly
        await db.refresh(scenario, ["initial_condition", "dambreak_params"])
        
        physics_parameters = {}
        if scenario.dambreak_params:
            physics_parameters["breach_width"] = scenario.dambreak_params.breach_width
            physics_parameters["formation_time"] = scenario.dambreak_params.formation_time
        if scenario.initial_condition:
            physics_parameters["initial_water_level"] = scenario.initial_condition.water_level
        
        job.status = JobStatus.PREPARING
        job.start_time = datetime.now(timezone.utc)
        await db.commit()
        
        # Instantiate correct engine
        config = {
            "scenario_type": scenario.scenario_type,
            "metadata": {"type": scenario.scenario_type},
            "time_control": {
                "duration_hours": scenario.simulation_duration,
                "timestep_seconds": scenario.timestep
            },
            "output_interval": scenario.output_interval,
            "physics_parameters": physics_parameters,
            "parameters": physics_parameters,
            "boundary_conditions": scenario.boundary_conditions or {},
            "source_datasets": scenario.source_datasets or []
        }
        
        engine_name = job.engine.upper()  # Normalize: "Delft3D" -> "DELFT3D"
        
        if engine_name == "SPH":
            engine = SPHEngine(config)
        elif engine_name == "DELFT3D":
            engine = Delft3DEngine(config)
        else:
            job.status = JobStatus.FAILED
            job.error = f"Unknown Engine: {job.engine}"
            await db.commit()
            return


        active_jobs[job.id] = engine

        # Prepare
        valid = engine.validate()
        if not valid:
            job.status = JobStatus.FAILED
            job.error = engine.error_message or "Validation failed"
            await db.commit()
            return
            
        engine.prepare()
        if engine.status == "FAILED":
            job.status = JobStatus.FAILED
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
            job.status = JobStatus.FAILED
            job.error = engine.error_message
        else:
            job.status = JobStatus.COMPLETED
            job.progress = 100.0
            
            # Post process results
            raw_results = engine.load_results()
            if raw_results:
                processed = InundationService.process_engine_output(raw_results)
                result_record = await InundationService.create_result_record(
                    db, job.project_id, job.scenario_id, job.engine, "EPSG:4326", processed
                )
                job.result_references = {"result_id": str(result_record.id)}
            
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
        status=JobStatus.QUEUED
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
