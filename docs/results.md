# Results and Inundation

Simulation engines map their outputs to `SimulationResult` entities.

## Inundation Post-Processing
`InundationService` applies a default `0.10m` threshold to raster outputs from engines. 
Cells below this threshold are discarded (Nodata) preventing small puddles/noise from skewing the statistical mean depth and maximum extent vectors.

## Artifact References
Instead of passing millions of pixels through JSON APIs, the `SimulationResult` records file paths (or S3 URIs) to output artifacts (TIFFs, GeoJSON polygons) and provides aggregated analytics (`max_depth_m`, `inundated_area_km2`).
