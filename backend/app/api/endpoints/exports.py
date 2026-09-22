from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import os

from app.db.session import get_db_session, async_session_factory
from app.models.export import ExportJob, ExportStatus
from app.models.result import SimulationResult
from app.schemas.export import ExportJobCreate, ExportJobRead
from app.services.export_service import ExportService

router = APIRouter()

async def background_export_task(job_id: uuid.UUID):
    async with async_session_factory() as db:
        job = await db.get(ExportJob, job_id)
        if not job:
            return
            
        result = await db.get(SimulationResult, job.result_id)
        
        job.status = ExportStatus.PROCESSING
        await db.commit()
        
        ExportService.process_export(job, result)
        
        await db.commit()

@router.post("/exports", response_model=ExportJobRead, status_code=202)
async def create_export(
    req: ExportJobCreate, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    result = await db.get(SimulationResult, req.result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Simulation Result not found")
        
    job = await ExportService.create_export_job(db, req.result_id, req.format)
    background_tasks.add_task(background_export_task, job.id)
    
    return job

@router.get("/exports/{job_id}", response_model=ExportJobRead)
async def get_export(job_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    job = await db.get(ExportJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Export Job not found")
    return job

@router.get("/exports/{job_id}/download")
async def download_export(job_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    job = await db.get(ExportJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Export Job not found")
        
    if job.status != ExportStatus.COMPLETED or not job.file_path:
        raise HTTPException(status_code=400, detail="Export is not completed yet")
        
    if not os.path.exists(job.file_path):
        raise HTTPException(status_code=404, detail="Export file missing from disk")
        
    return FileResponse(
        job.file_path, 
        filename=os.path.basename(job.file_path),
        media_type='application/octet-stream'
    )
