# Inundation Analysis

The framework extracts meaning from raw simulation outputs (raster grids of water elevation/depths) via the `InundationService`.

## Metrics
- **Max Depth (m)**: Calculated by taking the `max()` of the engine grid output.
- **Mean Depth (m)**: Calculated across the grid.
- **Inundated Area (km²)**: Calculated by summing the number of flooded cells and multiplying by the cell spatial resolution (converted to km²).

## Thresholds
By default, the analysis uses a depth threshold (`0.10m`) to prevent noise (like minimal rainwater pooling or numerical instability) from artificially inflating the inundated area calculation. All cells below `0.10m` are marked as nodata.
