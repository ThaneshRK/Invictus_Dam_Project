# Architecture

The system utilizes an asynchronous, event-driven pattern wrapping computationally blocking physics.

## Core Services
1. **API Layer (FastAPI)**: Validates incoming configurations against rigid Pydantic models. Refuses mathematically impossible parameters.
2. **Job Queue**: A local asynchronous memory dict (`active_jobs`) currently orchestrates tasks via `BackgroundTasks`. 
3. **Adapters**: Engines implement `SimulationEngine`. This abstracts away the difference between an internal python loop (`SPH`) and an external CLI executable (`Delft3D`).

## Database Model
All datasets, scenarios, and results tie hierarchically back to a strict UUID `Project` parent. Cross-referencing prevents users from simulating a project with another project's DEM raster. 
Instead of saving massive floating-point tensors into Postgres `bytea` columns, `SimulationResult` saves JSON references to physical paths (or object storage URIs), keeping DB dumps lightning fast.
