# Model Comparison Service

The comparison service provides scientific cross-validation between the generalized SPH prototype and Delft3D engine outputs.

## Alignment Protocol
Before any cell-by-cell statistical calculation, the service enforces strict spatial alignment:
- Identical CRS bounds.
- Matching grid resolutions.
- Invalid data (Nodata) masking to ensure we are only comparing cells where at least one model predicts water.

## Metrics Extracted
- **Intersection over Union (IoU)**: Evaluates flood footprint overlap. 
- **Depth Mean Absolute Error (MAE)**: Absolute error of depth predictions within the union mask.
- **Depth Root Mean Square Error (RMSE)**: Squaring the error heavily penalizes large local depth discrepancies between the models.

## Missing Engine Handling
If Delft3D is unavailable on the host system, the comparison API will gracefully report a `partial` status indicating the missing payload, rather than attempting to interpolate false comparisons.
