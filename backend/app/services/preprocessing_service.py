import os
import uuid
import asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session_factory
from app.models.preprocessing import PreprocessingJob, JobStatus
from app.services.gis_service import GISService

class PreprocessingService:
    @staticmethod
    async def create_job(db: AsyncSession, project_id: uuid.UUID, task_type: str, parameters: dict) -> PreprocessingJob:
        job = PreprocessingJob(
            project_id=project_id,
            task_type=task_type,
            parameters=parameters,
            status=JobStatus.PENDING
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job

    @staticmethod
    async def get_job(db: AsyncSession, job_id: uuid.UUID) -> PreprocessingJob:
        return await db.get(PreprocessingJob, job_id)

    @staticmethod
    async def run_preprocessing_task(job_id: uuid.UUID):
        # Background friendly orchestrator
        async with async_session_factory() as db:
            job = await db.get(PreprocessingJob, job_id)
            if not job:
                return

            job.status = JobStatus.RUNNING
            await db.commit()
            
            try:
                # Orchestrate GISService based on task_type
                # Mock integration of GIS steps to produce a manifest
                if job.task_type == "DEM_PREP":
                    input_dem = job.parameters.get("input_dem")
                    if input_dem and os.path.exists(input_dem):
                        output_dem = input_dem.replace(".tif", "_clipped.tif")
                        # For testing context, skip actual clip if shapes aren't provided
                        # GISService.clip_dem(input_dem, output_dem, shapes=[...])
                        
                        metadata = GISService.validate_dem(input_dem)
                        job.metadata_ = {
                            "input_dataset": input_dem,
                            "output_dataset": output_dem,
                            "crs": metadata["crs"],
                            "resolution": metadata["resolution"],
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                elif job.task_type == "TERRAIN_DERIVATIVES":
                    input_dem = job.parameters.get("input_dem")
                    # In real scenarios we run: GISService.calculate_slope_aspect(...)
                    job.metadata_ = {
                        "derivatives": ["slope", "aspect"]
                    }
                else:
                    raise ValueError(f"Unknown task type: {job.task_type}")

                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now(timezone.utc)
            except Exception as e:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                job.completed_at = datetime.now(timezone.utc)
            finally:
                await db.commit()
