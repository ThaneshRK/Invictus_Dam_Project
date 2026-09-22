# Database Strategy

The system uses **PostgreSQL** with the **PostGIS** extension for spatial data types and indexing.

## Schema Overview

### Projects Table (`projects`)
Organizes all workflows and boundaries.
- `id`: UUID (Primary Key)
- `name`: String
- `description`: Text
- `study_area`: PostGIS Geometry (Polygon/MultiPolygon, EPSG:4326)
- `crs`: String (Default EPSG:4326)

### Datasets Table (`datasets`)
Registers all ingested files to a specific project.
- `id`: UUID (Primary Key)
- `project_id`: UUID (Foreign Key -> projects.id)
- `name`: String
- `dataset_type`: Enum (DEM, river, dam, blockage, hydrological, satellite, exposure)
- `file_path`: String (Local disk path)
- `format`: String (GeoTIFF, GeoJSON, etc.)
- `crs`: String
- `bounding_box`: PostGIS Geometry (Polygon, EPSG:4326)
- `resolution`: Float
- `size`: Float (MB)
- `metadata_`: JSONB (Flexible storage for raster bands, vector columns, nodata values)

## Migrations
Database migrations are handled by **Alembic**.
To autogenerate migrations after model changes:
```bash
alembic revision --autogenerate -m "Description"
alembic upgrade head
```
