# Simulation Job Management

Running high-fidelity numerical physics (SPH, Delft3D) blocks HTTP workers. To preserve API health, Phase 9 delegates raw execution to a unified background worker via `BackgroundTasks` backed by the `SimulationJob` postgres table.

## Status Enums
Jobs cycle through:
- `QUEUED`: Accepted by FastAPI, waiting for loop execution.
- `PREPARING`: Building initial bounds, meshes, or fetching files.
- `RUNNING`: Core physics integration.
- `COMPLETED`: Simulation bounds processed and exported via `InundationService`.
- `FAILED` / `CANCELLED`.

## State Polling
Because we are using an in-memory `active_jobs` registry to proxy `engine.get_status()`, the `/api/v1/simulations/{id}/status` endpoint delivers live progress percentages (`0.0` - `100.0`) instead of relying solely on slow database commits.

## Architecture Path
Currently, the system is backed by local `asyncio` process thread execution. This interface natively sets up a future migration to RabbitMQ/Celery workers when clustered deployment is demanded.
