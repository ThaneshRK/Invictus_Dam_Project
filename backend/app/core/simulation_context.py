import uuid
import shapely.wkb
from typing import Optional, Dict, Any
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from geoalchemy2.shape import to_shape
import shapely.geometry
import json

from app.models.project import Project
from app.models.scenario import Scenario
from app.models.government import GovernmentDam, GovernmentReservoir, GovernmentRiver
from app.models.dataset import Dataset, DatasetCategory

class ScenarioDefinition(BaseModel):
    project_id: str
    dam_id: str
    reservoir_id: str
    river_id: str
    study_area: Dict[str, Any]
    dem_dataset_id: str
    hydrology_dataset_id: Optional[str]
    scenario_type: str
    scenario_parameters: Dict[str, Any]

class SimulationInputContext:
    def __init__(self, 
                 project: Project, 
                 dam: GovernmentDam, 
                 reservoir: GovernmentReservoir, 
                 river: GovernmentRiver, 
                 study_area: Any, 
                 dem: Dataset, 
                 hydrology: Optional[Dataset], 
                 scenario: Scenario):
        self.project = project
        self.dam = dam
        self.reservoir = reservoir
        self.river = river
        self.study_area = study_area
        self.dem = dem
        self.hydrology = hydrology
        self.scenario = scenario
        
    @classmethod
    async def build(cls, db: AsyncSession, project_id: uuid.UUID, scenario_id: uuid.UUID) -> "SimulationInputContext":
        import logging
        logger = logging.getLogger(__name__)
        
        # 1. Resolve Project
        project = await db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
            
        # 2. Resolve Scenario
        scenario = await db.get(Scenario, scenario_id)
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
            
        if scenario.project_id != project.id:
            raise HTTPException(status_code=400, detail="Scenario does not belong to project")
            
        # 3. Resolve Dam, Reservoir, River
        if not project.selected_dam_id:
            raise HTTPException(status_code=400, detail="Project missing selected dam")
        if not project.selected_reservoir_id:
            raise HTTPException(status_code=400, detail="Project missing selected reservoir")
        if not project.selected_river_id:
            raise HTTPException(status_code=400, detail="Project missing selected river")
            
        dam = await db.get(GovernmentDam, project.selected_dam_id)
        if not dam:
            raise HTTPException(status_code=404, detail="Selected dam not found")
            
        reservoir = await db.get(GovernmentReservoir, project.selected_reservoir_id)
        if not reservoir:
            raise HTTPException(status_code=404, detail="Selected reservoir not found")
            
        river = await db.get(GovernmentRiver, project.selected_river_id)
        if not river:
            raise HTTPException(status_code=404, detail="Selected river not found")
            
        # 4. Resolve Study Area
        if not project.study_area:
            raise HTTPException(status_code=400, detail="Project missing study area")
            
        # 5. Resolve DEM — auto-provision from OpenTopography if not manually uploaded
        dem = None
        if project.dem_dataset_id:
            try:
                dem_uuid = uuid.UUID(project.dem_dataset_id)
                dem = await db.get(Dataset, dem_uuid)
            except (ValueError, Exception):
                dem = None
        
        if not dem:
            # Auto-provision DEM from OpenTopography using study area bounds (with synthetic fallback)
            logger.info(f"Auto-provisioning DEM for project {project_id}...")
            try:
                from geoalchemy2.shape import to_shape
                study_geom = to_shape(project.study_area)
                bounds = study_geom.bounds  # (minx, miny, maxx, maxy)
                
                import tempfile, os
                output_dir = os.path.join("/tmp", "dem_cache", str(project_id))
                os.makedirs(output_dir, exist_ok=True)
                
                dem_file_path = None
                dataset_name = "OpenTopography SRTMGL1 (Auto)"
                source_type = "OpenTopography"
                is_synthetic = False
                res_val = 30.0

                try:
                    from app.services.government_data.providers_impl import OpenTopographyDEMProvider
                    dem_provider = OpenTopographyDEMProvider()
                    terrain = await dem_provider.acquire_dem(bounds, "EPSG:4326", output_dir)
                    dem_file_path = terrain.local_file
                    res_val = terrain.resolution
                except Exception as opentopo_err:
                    logger.warning(f"OpenTopography DEM acquisition failed ({opentopo_err}). Falling back to synthetic terrain raster for study area bounds.")
                    import rasterio
                    from rasterio.transform import from_origin
                    import numpy as np
                    
                    minx, miny, maxx, maxy = bounds
                    res_deg = 0.0002777777777777778  # ~30m
                    cols = max(20, int(abs(maxx - minx) / res_deg))
                    rows = max(20, int(abs(maxy - miny) / res_deg))
                    
                    transform = from_origin(minx, maxy, res_deg, res_deg)
                    x = np.linspace(0, 1, cols)
                    y = np.linspace(0, 1, rows)
                    xx, yy = np.meshgrid(x, y)
                    # Generate realistic valley terrain (700m down to 250m elevation)
                    data = (700.0 - 400.0 * xx - 100.0 * yy + 30.0 * np.sin(xx * np.pi * 2)).astype(np.float32)
                    
                    synth_path = os.path.join(output_dir, f"synthetic_dem_{project_id}.tif")
                    with rasterio.open(
                        synth_path, 'w', driver='GTiff',
                        height=rows, width=cols, count=1,
                        dtype=data.dtype, crs='EPSG:4326',
                        transform=transform
                    ) as dst:
                        dst.write(data, 1)
                        
                    dem_file_path = synth_path
                    dataset_name = "Synthetic DEM Terrain (Static Fallback)"
                    source_type = "Synthetic Generator"
                    is_synthetic = True

                # Create a Dataset record for the auto-provisioned DEM
                from shapely.geometry import box
                from geoalchemy2.shape import from_shape
                bbox_geom = box(bounds[0], bounds[1], bounds[2], bounds[3])
                
                dem = Dataset(
                    project_id=project.id,
                    name=dataset_name,
                    dataset_type=DatasetCategory.DEM,
                    file_path=dem_file_path,
                    format="GeoTIFF",
                    crs="EPSG:4326",
                    bounding_box=from_shape(bbox_geom, srid=4326),
                    resolution=res_val,
                    metadata_={
                        "source": source_type,
                        "auto_provisioned": True,
                        "is_synthetic": is_synthetic
                    }
                )
                db.add(dem)
                project.dem_dataset_id = str(dem.id)
                await db.commit()
                await db.refresh(dem)
                logger.info(f"DEM auto-provisioned successfully: {dem.id} (synthetic={is_synthetic})")
            except Exception as e:
                logger.error(f"DEM auto-provisioning failed: {e}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"DEM auto-provisioning failed: {str(e)}"
                )
        
        # 6. Hydrology — auto-link from government static fixtures if available
        hydrology = None
        if scenario.source_datasets:
            for ds_id_str in scenario.source_datasets:
                try:
                    ds_id = uuid.UUID(str(ds_id_str))
                    ds = await db.get(Dataset, ds_id)
                    if ds and ds.dataset_type == DatasetCategory.hydrological:
                        hydrology = ds
                        break
                except (ValueError, Exception):
                    continue

        if scenario.scenario_type == "WATER_RELEASE" and not hydrology and not (scenario.parameters and scenario.parameters.get("constant_discharge")):
            raise HTTPException(status_code=400, detail="Required hydrological data is missing for WATER_RELEASE")
            
        # 7. Scenario parameters validation
        if not scenario.parameters:
            raise HTTPException(status_code=400, detail="Scenario parameters are invalid or missing")
            
        return cls(
            project=project,
            dam=dam,
            reservoir=reservoir,
            river=river,
            study_area=project.study_area,
            dem=dem,
            hydrology=hydrology,
            scenario=scenario
        )

    def to_scenario_definition(self) -> ScenarioDefinition:
        study_area_geojson = {}
        try:
            if hasattr(self.study_area, 'data'):
                geom = to_shape(self.study_area)
                study_area_geojson = shapely.geometry.mapping(geom)
        except Exception as e:
            study_area_geojson = {"type": "Polygon", "coordinates": []}
            
        return ScenarioDefinition(
            project_id=str(self.project.id),
            dam_id=str(self.dam.id),
            reservoir_id=str(self.reservoir.id),
            river_id=str(self.river.id),
            study_area=study_area_geojson,
            dem_dataset_id=str(self.dem.id),
            hydrology_dataset_id=str(self.hydrology.id) if self.hydrology else None,
            scenario_type=self.scenario.scenario_type.value if hasattr(self.scenario.scenario_type, 'value') else str(self.scenario.scenario_type),
            scenario_parameters=self.scenario.parameters or {}
        )
