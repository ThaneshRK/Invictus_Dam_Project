# Data Validation Standards

To ensure academic transparency and robust CI/CD, the framework explicitly labels the source of generated arrays and polygons.

## Labeling
- **REAL SIMULATION**: Mathematics computed live by the `SPHSolver` or `Delft3DEngine`.
- **TEST FIXTURE**: The result of a bypassed operation. Used explicitly when an external binary (Delft3D) or API (GEE) cannot authenticate or does not exist on the host system.
- **DEMO MODE**: Hardcoded parameter assumptions provided in `examples/india_demo/config.json`.

## Restrictions
1. The framework **WILL NOT** fabricate scientific results. If Delft3D fails to run, it returns a fixture and sets `status = partial/fixture`, rather than inventing a flood extent and passing it off as a physical computation.
2. The HADR Exposure module **WILL NOT** fabricate monetary damage functions (e.g. `$2M structural loss`). It only reports pure intersection metrics (e.g. `120 structures exposed`).
