import os
import shutil
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db_session
from app.models.asset import Dam3DAsset
from app.schemas.asset import Dam3DAssetRead, Dam3DAssetUpdate
from app.core.config import settings
import struct

router = APIRouter()

STORAGE_DIR = "storage/3d_assets"
os.makedirs(STORAGE_DIR, exist_ok=True)

def validate_glb(filepath: str) -> bool:
    size = os.path.getsize(filepath)
    if size == 0:
        return False
    with open(filepath, 'rb') as f:
        magic = f.read(4)
        if magic != b'glTF':
            return False
        version = struct.unpack('<I', f.read(4))[0]
        if version != 2:
            return False
    return True

@router.post("/{project_id}/assets", response_model=Dam3DAssetRead)
async def upload_asset(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session)
):
    if not file.filename.lower().endswith(".glb"):
        raise HTTPException(status_code=400, detail="Only .glb files are supported")
    
    asset_id = uuid.uuid4()
    filename = f"{asset_id}_{file.filename}"
    filepath = os.path.join(STORAGE_DIR, filename)
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    if not validate_glb(filepath):
        os.remove(filepath)
        raise HTTPException(status_code=400, detail="Invalid GLB file")
        
    asset = Dam3DAsset(
        id=asset_id,
        project_id=project_id,
        file_path=filepath,
        asset_format="GLB",
        origin_lat=0.0,
        origin_lon=0.0,
        origin_elevation=0.0,
        rotation_x=0.0,
        rotation_y=0.0,
        rotation_z=0.0,
        scale_x=1.0,
        scale_y=1.0,
        scale_z=1.0,
        source="upload",
        units="meters",
        coordinate_reference_system="EPSG:4326"
    )
    
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    
    return asset

@router.get("/{project_id}/assets", response_model=List[Dam3DAssetRead])
async def get_assets(project_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Dam3DAsset).filter(Dam3DAsset.project_id == project_id))
    return result.scalars().all()

@router.put("/assets/{asset_id}", response_model=Dam3DAssetRead)
async def update_asset(asset_id: uuid.UUID, asset_update: Dam3DAssetUpdate, db: AsyncSession = Depends(get_db_session)):
    asset = await db.get(Dam3DAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    update_data = asset_update.model_dump(exclude_unset=True) if hasattr(asset_update, 'model_dump') else asset_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(asset, key, value)
        
    await db.commit()
    await db.refresh(asset)
    return asset
