# Phase 3A.1 — Bhakra Real Data Acquisition Specification

## 1. Executive Summary
This report specifies the exact external data required to execute the first genuine Bhakra `DAM_BREAK` simulation through SPH2D, SPH3D, and Delft3D using the existing application implementation. The existing codebase and datasets have been audited to determine exact technical requirements. 

**Status:** BLOCKED_NEEDS_DATA_SOURCE

## 2. Existing Bhakra Data Inventory

Based on an inspection of the local shapefiles (`dam.zip`, `Reservoir.zip`, `Rivers.zip`), the following records represent the test case:

*   **Bhakra Dam** (Point)
    *   **Coordinates:** Lat 31.41146286, Lon 76.43337239
    *   **Projected (LCC):** X = 3664633.3, Y = 4811845.4
    *   **Attributes:** `dm_name` = Bhakra Dam, `rivcode` = Satluj, `dm_type` = TE + PG, `dm_cmp_yr` = 1963.
    *   **Elevation/Water Level Info:** None present in the dataset.

*   **Bhakra Reservoir / Govind Sagar** (Polygon)
    *   **CRS:** WGS_1984_Lambert_Conformal_Conic
    *   **Geometry Bounds (LCC):** X: [3658178, 3695662], Y: [4791776, 4831933]
    *   **Attributes:** `wbname` = Bhakra, `area_ha` = 14262.7
    *   **Elevation/Water Level Info:** None present in the dataset.

*   **Sutlej River** (LineString)
    *   **Attributes:** `rivname` = Satluj, `ba_name` = Indus (Up to border).

**Relationships & Matching Confidence:**
*   **Dam ↔ River:** The relationship is explicit only via string matching (`rivcode` == `rivname` == "Satluj"). There is no formal foreign key. Confidence: Medium.
*   **Dam ↔ Reservoir:** There is NO explicit relational link (no shared ID). The relationship must be established spatially or by string matching (e.g., both names contain "Bhakra"). Confidence: Medium.

## 3. Actual Engine Input Requirements

An inspection of `SPHInputBuilder`, `SPHSolverBase`, and `Delft3DModelBuilder` reveals the following strict requirements:

*   **DEM as the Simulation Domain:** Both the SPH and Delft3D engines extract their simulation domain bounds *directly from the DEM extent* (`src.bounds.left`, `src.bounds.right`, etc.). **The DEM file *is* the computational domain.** If you provide a 500x500 km DEM, the engines will attempt to simulate a 500x500 km area.
*   **DEM CRS:** Must be a **Projected Coordinate System** (meters). SPH calculates particle volumes and physical forces (gravity, gradients) assuming X/Y are in meters. Geographic CRS (Lat/Lon) will result in absurd physical gradients.
*   **DEM Resolution:** There is no hardcoded limitation on resolution, but **SPH enforces a `MAX_SPH_PARTICLES = 50000` limit**. At a 30m spacing, 50,000 particles can cover a maximum of **45 sq km**. The reservoir alone is 142 sq km. Therefore, to simulate the full reservoir and downstream area in SPH, the `particle_spacing` must be dynamically scaled up (e.g., ~100m–150m spacing), or the DEM must be aggressively cropped around the immediate breach zone.
*   **Initial Water Level:** `initial_water_level` (in meters) is a strictly required scalar value. In SPH, it is compared against the DEM `z_b` elevation to spawn water particles. In Delft3D, it sets `WaterLevIni`.

## 4. Required Simulation Domain

Because the engine uses the entire DEM bounds as the computational domain, you must acquire a DEM that is *pre-cropped* to the minimum viable area containing the reservoir and the immediate downstream floodplain.

*   **LCC Bounds (Approx):** X: [3630000, 3700000], Y: [4790000, 4840000]
*   **WGS84 Extent (Approx):**
    *   Min Longitude: 76.10° E
    *   Max Longitude: 76.85° E
    *   Min Latitude: 31.15° N
    *   Max Latitude: 31.65° N
*   **Dimensions:** ~70 km wide × ~50 km high (~3500 sq km).
*   **Note:** This is too large for SPH at 30m resolution. SPH particle spacing will need to be configured to >= 250m to fit within the 50,000 particle limit for this extent, or the DEM must be cropped much smaller for SPH tests. Delft3D can handle the 30m resolution over this domain.

## 5. DEM Acquisition Specification

*   **Dataset:** CartoDEM V3 (30m) via ISRO Bhuvan, or SRTM 1-Arc Second Global (30m) via USGS EarthExplorer.
*   **Format:** GeoTIFF (`.tif`).
*   **CRS:** Must be reprojected to UTM Zone 43N (EPSG:32643) or India LCC.
*   **Vertical Units:** Meters (referenced to MSL).
*   **Action:** Download, merge, reproject to meters, and **crop to the bounds specified in Section 4** before uploading.

## 6. Initial Water Level Acquisition Specification

The `DAM_BREAK` scenario strictly requires a defensible initial water surface elevation (in MSL).
*   **Source:** Central Water Commission (CWC) Reservoir Level Bulletins or official Bhakra Beas Management Board (BBMB) data.
*   **Value:** Bhakra Dam Full Reservoir Level (FRL) is approximately **512 meters MSL**.
*   **Action:** Enter this scalar value into the scenario parameters (`initial_water_level`). No API integration is currently available or required to supply this single value for the first run.

## 7. Storage Requirement Analysis

**Storage is NOT REQUIRED.**
Inspection of `SPHSolverBase.init_real_scenario` shows that reservoir storage is not an input parameter. SPH dynamically computes the initial volume by placing particles wherever the DEM terrain is below the `initial_water_surface_elevation` within the reservoir bounding box.

## 8. Hydrology Requirement Analysis

**NO CONTINUOUS HYDROGRAPH REQUIRED FOR FIRST DAM_BREAK RUN.**
The current implementation of `DAM_BREAK` for both Delft3D and SPH relies solely on the initial reservoir water level and the physical breach mechanism (Verheij-van der Knaap). Upstream inflow is ignored, and downstream boundary conditions are automatically set to open (water level = 0 or initial).

## 9. Required Now / Later / Not Required

**A. REQUIRED NOW**
*   **Cropped DEM GeoTIFF** (Projected to meters, extent matching Section 4).
*   **Initial Water Level** (Scalar parameter: ~512m).

**B. REQUIRED LATER**
*   Continuous upstream inflow CSV hydrographs (for `WATER_RELEASE`).

**C. NOT REQUIRED FOR FIRST DAM_BREAK RUN**
*   Reservoir Storage Volume.
*   River Discharge telemetry.
*   Downstream boundary hydrographs.

## 10. Exact Validation Commands

Use these commands to validate the DEM *before* using it in the system:

```bash
# 1. Verify Format, Dimensions, and Resolution (ensure resolution is in meters, e.g., 30 30)
gdalinfo datasets/bhakra_dem_cropped.tif | grep -E 'Driver|Size is|Pixel Size'

# 2. Verify CRS is projected (should NOT be geographic lat/lon)
gdalinfo -proj4 datasets/bhakra_dem_cropped.tif

# 3. Verify Bounding Box (should match the tight cropped domain)
gdalinfo datasets/bhakra_dem_cropped.tif | grep -A 4 'Corner Coordinates'

# 4. Verify Min/Max Elevation and NoData values
gdalinfo -stats datasets/bhakra_dem_cropped.tif | grep -E 'Minimum|NoData'
```

## 11. Blocking Issues

*   The system lacks a real, projected, pre-cropped GeoTIFF DEM for the Bhakra region. The SPH and Delft3D engines will immediately crash or produce garbage physics without it.

## 12. Recommended Next Action

Do not write code. An operator must manually download the SRTM or CartoDEM tiles for the Bhakra region, mosaic them, reproject to UTM Zone 43N, crop to the tight bounding box defined in Section 4, and place the resulting `bhakra_dem_cropped.tif` into the `datasets/` directory.

BLOCKED_NEEDS_DATA_SOURCE
