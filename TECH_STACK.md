# Tech Stack Specification

This document details the complete technology stack used across the **Generalized Flood Simulation & HADR Framework**.

---

## 🏗️ System Overview

The framework is built as a microservice-ready, containerized application designed for GIS data preprocessing, 2D hydrodynamic flood simulation (SPH & Delft3D), remote sensing validation (Google Earth Engine), and Humanitarian Assistance & Disaster Relief (HADR) impact assessment.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        React 19 + TypeScript + Vite                     │
│                    (Deck.gl 9, Leaflet, MapLibre, Recharts)             │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ REST / HTTP
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       FastAPI Backend (Python 3.11)                     │
├───────────────────┬─────────────────────┬───────────────────────────────┤
│   GIS & Rasters   │  Physics Engines    │   HADR & Satellite Validation │
│ (GDAL/Rasterio/   │  (Internal SPH /    │  (Google Earth Engine API /   │
│   GeoPandas)      │   Delft3D Adapter)  │      OpenStreetMap Data)      │
└───────────────────┴──────────┬──────────┴───────────────────────────────┘
                               │ Async ORM (SQLAlchemy 2.0 / Asyncpg)
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    PostgreSQL 15 + PostGIS 3.3 Database                 │
└────────────────────────────────────┴────────────────────────────────────┘
```

---

## 🎨 Frontend Stack

| Category | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Framework** | [React](https://react.dev/) | `^19.2.8` | Component-based User Interface |
| **Language** | [TypeScript](https://www.typescriptlang.org/) | `~6.0.2` | Type-safe front-end development |
| **Build Tooling** | [Vite](https://vitejs.dev/) | `^8.3.0` | Ultra-fast module bundler & dev server |
| **Spatial Maps** | [Leaflet](https://leafletjs.com/) & [React-Leaflet](https://react-leaflet.js.org/) | `^1.9.4` / `^5.0.0` | Interactive 2D map views & layer rendering |
| **Map Drawing** | [Leaflet-Draw](https://github.com/Leaflet/Leaflet.draw) | `^1.0.4` | ROI and bounding box drawing tools |
| **3D & Layer Visualization** | [Deck.gl](https://deck.gl/) | `^9.4.0` | High-performance WebGL geospatial data rendering |
| **Vector Tiles & Basemaps** | [MapLibre GL](https://maplibre.org/) | `^6.9.1` | MapLibre vector map rendering |
| **Charts & Analytics** | [Recharts](https://recharts.org/) | `^3.10.1` | Hydrographs, depth distributions, and comparison charts |
| **Icons** | [Lucide React](https://lucide.dev/) | `^1.46.0` | Modern SVG iconography |
| **HTTP Client** | [Axios](https://axios-http.com/) | `^1.20.0` | REST API requests to backend |
| **Linter** | [Oxlint](https://oxc-project.github.org/) | `^1.81.0` | High-performance JavaScript/TypeScript linter |
| **Production Web Server** | [Nginx](https://nginx.org/) | `alpine` | Static asset serving in production Docker container |

---

## ⚙️ Backend Stack

| Category | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Language** | [Python](https://www.python.org/) | `3.11` | Backend core programming language |
| **Web Framework** | [FastAPI](https://fastapi.tiangolo.com/) | `>=0.103.0` | High-performance asynchronous REST API framework |
| **ASGI Server** | [Uvicorn](https://www.uvicorn.org/) | `>=0.23.2` | Asynchronous Web Server Gateway Interface |
| **Data Validation** | [Pydantic](https://docs.pydantic.dev/) & Pydantic-Settings | `>=2.4.0` | Schema validation and environment management |
| **Database ORM** | [SQLAlchemy](https://www.sqlalchemy.org/) | `>=2.0.20` | Asynchronous Object Relational Mapper |
| **Database Drivers** | [asyncpg](https://github.com/MagicStack/asyncpg) & [psycopg2-binary](https://psycopg.org/) | `>=0.28.0` / `>=2.9.7` | PostgreSQL database adapters |
| **DB Migrations** | [Alembic](https://alembic.sqlalchemy.org/) | `>=1.12.0` | Database schema migrations management |
| **Testing** | [Pytest](https://docs.pytest.org/) & `pytest-asyncio` | `>=7.4.2` | Automated unit and integration testing suite |
| **Async HTTP Client** | [HTTPX](https://www.python-httpx.org/) | `>=0.25.0` | Asynchronous HTTP requests |

---

## 🌐 Geospatial & Hydrodynamic Data Libraries

| Library | Version | Purpose |
| :--- | :--- | :--- |
| **[GDAL](https://gdal.org/)** | System native (`gdal-bin`, `libgdal-dev`) | Core C++ Geospatial Data Abstraction Library |
| **[Rasterio](https://rasterio.readthedocs.io/)** | `>=1.3.8` | GeoTIFF/DEM raster processing, cropping, and resampling |
| **[GeoPandas](https://geopandas.org/)** | `>=0.14.0` | Spatial dataframes for vector geometries (GeoJSON, SHP) |
| **[Shapely](https://shapely.readthedocs.io/)** | `>=2.0.1` | Planar spatial geometry operations & analysis |
| **[PyProj](https://pyproj4.github.io/pyproj/)** | `>=3.6.0` | Cartographic projections & Coordinate Reference System (CRS) transformations |
| **[SciPy](https://scipy.org/) & [NumPy](https://numpy.org/)** | `>=1.11.0` | Vectorized numerical computations and matrix solvers |
| **[Xarray](https://docs.xarray.dev/)** | `>=2024.1.0` | N-dimensional labeled array processing for hydraulic grids |
| **[NetCDF4](https://unidata.github.io/netcdf4-python/) & [h5netcdf](https://h5netcdf.org/)** | `>=1.6.5` / `>=1.3.0` | NetCDF dataset reading and storage |
| **[MeshKernel](https://github.com/Deltares/MeshKernelPy)** | `>=8.3.0` | Unstructured grid generation and manipulation (Deltares) |
| **[Xugrid](https://xugrid.readthedocs.io/)** | `>=0.15.3` | Unstructured grid data analysis based on Xarray |

---

## 🌊 Physics & Hydrodynamic Simulation Engines

1. **Smoothed Particle Hydrodynamics (SPH) Engine**:
   - Internal Python/NumPy/SciPy numerical implementation.
   - Particle-based meshless solver for transient dam breach fluid flows.
2. **Delft3D Engine**:
   - External hydrodynamic solver adapter (Deltares Delft3D).
   - Generates `.mdf` grid definitions and executes hydrodynamic simulations via CLI subprocess orchestration.

---

## 🛰️ Remote Sensing & HADR Analytics

- **Google Earth Engine API** (`earthengine-api>=0.1.370`): Connects to Earth Engine for Sentinel-1 SAR satellite imagery fetch and real-world flood extent extraction.
- **OpenStreetMap HADR Exposure Analysis**: Spatial intersection of maximum flood footprints with building footprints and road networks to calculate population and infrastructure exposure.
- **National Register of Large Dams (NRLD)**: Government data integration service for Indian dam safety and reservoir metadata.

---

## 🗄️ Database Stack

- **Database Engine**: [PostgreSQL 15](https://www.postgresql.org/)
- **Spatial Extension**: [PostGIS 3.3](https://postgis.net/) (`postgis/postgis:15-3.3`)
- **Spatial Integration**: [GeoAlchemy2](https://geoalchemy-2.readthedocs.io/) (`>=0.14.1`) for spatial SQL query execution in SQLAlchemy.

---

## 🐳 DevOps & Infrastructure

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Container Engine** | Docker & Docker Compose | Multi-container stack specification (`docker-compose.yml`) |
| **Backend Image** | `python:3.11-slim` | Debian-based slim Python environment with GDAL & C++ build tools |
| **Frontend Build** | `node:20-alpine` -> `nginx:alpine` | Multi-stage Docker build producing lightweight Nginx container |
| **Database Container** | `postgis/postgis:15-3.3` | Spatial database container |
| **Orchestration Scripts** | Bash (`scripts/start-docker.sh`) | Single command spin-up and healthcheck verification |

---
