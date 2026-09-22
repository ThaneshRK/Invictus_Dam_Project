from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.db.session import get_db_session
from app.models.preprocessing import PreprocessingJob
from app.schemas.preprocessing import PreprocessingJobCreate, PreprocessingJobRead
from app.services.preprocessing_service import PreprocessingService
from app.models.project import Project

router = APIRouter()

@router.post("/projects/{project_id}/preprocessing", response_model=PreprocessingJobRead, status_code=202)
async def create_preprocessing_job(
    project_id: uuid.UUID,
    job_in: PreprocessingJobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    job = await PreprocessingService.create_job(db, project_id, job_in.task_type, job_in.parameters or {})
    
    # Launch in background
    background_tasks.add_task(PreprocessingService.run_preprocessing_task, job.id)
    
    return job

@router.get("/preprocessing/{job_id}", response_model=PreprocessingJobRead)
async def get_preprocessing_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    job = await PreprocessingService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.get("/preprocessing/{job_id}/status")
async def get_preprocessing_job_status(job_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    job = await PreprocessingService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": job.status, "task_type": job.task_type}
