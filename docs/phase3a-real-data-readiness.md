# Phase 3A — Real Data Readiness Audit

## 1. Selected Test Case
**Test Case Identified:** Bhakra Dam
- **Coordinates:** 31.4114° N, 76.4333° E (from government Dam dataset `Dam.shp`)
- **River System:** Sutlej River
- **Reservoir:** Govind Sagar (`Reservoir.shp`)

## 2. Required DEM Specification
To support the configured SPH and Delft3D input builders (`app/engines/sph/builder.py`, `app/engines/delft3d/builder.py`), the Digital Elevation Model (DEM) must meet the following technical criteria:
- **File Format:** GeoTIFF (`.tif`)
- **CRS:** Projected Coordinate System in meters (e.g., EPSG:32643 - UTM Zone 43N). Geographic coordinates (Lat/Lon in degrees) are explicitly blocked by the SPH coordinate logic.
- **Horizontal Resolution:** Minimum 30 meters (to resolve breach features and downstream river banks).
- **Vertical Units:** Meters.
- **Vertical Datum:** MSL (Mean Sea Level) or compatible with initial water level configurations.
- **Geographic Extent (Approximate):**
  - Minimum Longitude: 76.0° E
  - Maximum Longitude: 76.9° E
  - Minimum Latitude: 31.0° N
  - Maximum Latitude: 31.9° N
- **NoData Handling:** Standard NoData values (e.g., -9999 or NaN) should be used, but the computational domain mask must cover the entire Dam + Reservoir + downstream River.

## 3. Hydrology Requirements (Scenario-Specific)
Based on `backend/app/models/scenario.py` and the engine builders:

### A. Catastrophic Dam Break
- **Required:** Initial water level (meters), Reservoir storage volume (for verification), Breach geometry.
- **Optional:** Inflow hydrograph (if simulating continuous inflow during failure).
- **Timestamp Requirements:** N/A (Runs on a relative elapsed time index, $T_0 = 0$).

### B. Controlled Water Release
- **Required:** Discharge boundary condition curve (Hydrograph `Q(t)`).
- **Units:** Discharge in m³/s, Time in minutes/seconds.
- **Required Format:** CSV mapping time (relative or absolute) to discharge.

### C. River Blockage/Landslide
- **Required:** Upstream river discharge to fill the blocked river valley (Constant `Q` or `Q(t)`).
- **Units:** m³/s.

## 4. First Real Test Scenario
**Recommended First Scenario:** Catastrophic Dam Break (`DAM_BREAK`).
**Why:** It is the simplest scientifically defensible scenario to execute first. It requires **no continuous hydrological CSV datasets**. It only requires a valid DEM and a single scalar value for `initial_water_level` at the dam. The structural failure is computed internally using the Verheij-van der Knaap equations natively implemented in Delft3D and the breach scripts for SPH.

## 5. Existing Provider Support
A review of `backend/app/services/government_data/` reveals:
- **`NRLDProvider`**: Implemented (reads local static `dam.zip`).
- **`LocalDatasetWaterProvider`**: Reads local static `Reservoir.zip` but **mocks** live parameters (`current_water_level_m = 50.0`, `storage_percentage = 75.0`).

## 6. Missing Provider Support
Live, real-time government API support for the following is currently **NOT IMPLEMENTED**:
- Reservoir level
- Reservoir storage
- River discharge
- River water level

## 7. Exact Data Acquisition Requirements
To unblock Phase 3, the following datasets must be acquired externally and placed into the system:

### DEM
- **Extent:** Lat: 31.0°N to 31.9°N, Lon: 76.0°E to 76.9°E
- **Resolution:** 30m or finer (e.g., CartoDEM or SRTM 30m).
- **CRS:** UTM Zone 43N (EPSG:32643) or equivalent projected system.
- **Format:** GeoTIFF (`.tif`).
- **Vertical Units:** Meters.

### Hydrology (Only if running WATER_RELEASE)
- **Station/River:** Sutlej River (at or downstream of Bhakra)
- **Parameter:** Discharge (m³/s)
- **Format:** CSV with exact column headers `timestamp` and `value`.

## 8. Validation Procedure
Before attempting to run the engine, use these shell commands to validate the downloaded datasets (Do not modify the application):

**DEM Validation (`gdalinfo`):**
```bash
# Check CRS, Extent, Resolution, and NoData values
gdalinfo datasets/dem.tif | grep -E 'Coordinate System|Pixel Size|NoData|Corner Coordinates'
```

**Hydrology CSV Validation (`head` and `awk`):**
```bash
# Verify headers exactly match "timestamp" and "value"
head -n 1 datasets/hydrograph.csv

# Verify timestamps are ISO8601 and values are numeric
awk -F',' 'NR>1 {print $1, $2}' datasets/hydrograph.csv | head
```

## 9. What is required to unblock Phase 3
To unblock Phase 3, you must physically download the Bhakra DEM (projected to UTM, GeoTIFF) covering the coordinates listed in Section 7, and upload it via the API or place it in the datasets directory to satisfy the `SimulationInputContext` strict validation checks.
