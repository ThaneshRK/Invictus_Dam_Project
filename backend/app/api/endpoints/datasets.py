from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uuid
from typing import List

from app.db.session import get_db_session
from app.models.dataset import Dataset, DatasetCategory
from app.models.project import Project
from app.schemas.dataset import DatasetRead
from app.services.dataset_service import DatasetService

router = APIRouter()

@router.post("/projects/{project_id}/datasets", response_model=DatasetRead, status_code=201)
async def upload_dataset(
    project_id: uuid.UUID, 
    name: str = Form(...),
    dataset_type: DatasetCategory = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session)
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    file_path, metadata = await DatasetService.process_upload(project_id, file)
    
    dataset = Dataset(
        project_id=project_id,
        name=name,
        dataset_type=dataset_type,
        file_path=file_path,
        format=metadata.get('format'),
        crs=metadata.get('crs'),
        bounding_box=metadata.get('bounding_box'),
        resolution=metadata.get('resolution'),
        size=metadata.get('size'),
        metadata_=metadata.get('metadata_')
    )
    
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    
    return dataset

@router.get("/projects/{project_id}/datasets", response_model=List[DatasetRead])
async def list_project_datasets(project_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Dataset).where(Dataset.project_id == project_id))
    return result.scalars().all()

@router.get("/datasets/{dataset_id}", response_model=DatasetRead)
async def read_dataset(dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    dataset = await db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset
