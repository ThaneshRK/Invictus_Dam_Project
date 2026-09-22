# Scenario Engine Configurations

The Framework abstracts hydraulic scenarios away from specific solver implementations (like Delft3D or SPH-based models) by using a generalized Scenario entity.

## Unified Scenario Model
Each `Scenario` represents a single simulation run configuration containing:
- **Time Controls**: `simulation_duration` (hours), `timestep` (seconds), `output_interval` (seconds).
- **Physics Parameters**: Extracted via `DAM_BREAK`, `WATER_RELEASE`, or `RIVER_BLOCKAGE` specific schemas.
- **Dataset Links**: References to ingested DEMs and vector geometries.

## Serialization Format
When hitting `POST /api/v1/scenarios/{id}/validate`, the service confirms all datasets are present and valid, then serializes a solver-agnostic JSON payload. Future simulation engines (built in Phase 4+) will ingest this structure:

```json
{
  "version": "1.0",
  "metadata": {
    "scenario_id": "uuid",
    "name": "Catastrophic Breach",
    "type": "DAM_BREAK"
  },
  "time_control": {
    "duration_hours": 24.0,
    "timestep_seconds": 1.0,
    "output_interval_seconds": 60.0
  },
  "physics_parameters": {
    "initial_water_level": 100.0,
    "reservoir_volume": 1000000.0,
    "breach_width": 50.0,
    "breach_height": 20.0,
    "breach_elevation": 80.0,
    "breach_formation_time": 2.0,
    "initial_downstream_condition": 0.5
  },
  "boundary_conditions": {},
  "inputs": {
    "datasets": ["uuid-of-dem", "uuid-of-dam-shape"]
  }
}
```
