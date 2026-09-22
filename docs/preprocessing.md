# Preprocessing Orchestration

To avoid blocking the main API thread during heavy GIS operations, the system employs a background-friendly architecture.

## PreprocessingJob Model
Every preprocessing request creates a `PreprocessingJob` with:
- `status`: PENDING, RUNNING, COMPLETED, or FAILED
- `metadata_`: A JSON manifest detailing inputs, output artifacts, scaling parameters, and timestamps.

## Flow
1. Client POSTs a job configuration to `/api/v1/projects/{id}/preprocessing`.
2. Server immediately returns a `202 Accepted` response with the `job_id`.
3. Background task (`asyncio` based or `FastAPI.BackgroundTasks`) picks up the task and begins GIS operations.
4. Client polls `/api/v1/preprocessing/{job_id}/status` to detect completion.
