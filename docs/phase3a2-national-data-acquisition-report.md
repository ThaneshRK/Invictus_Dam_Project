# Phase 3A.2 — National India-Wide Real Data Acquisition Report

## 1. Executive Summary
This report details the implementation of a generalized, provider-independent data acquisition architecture for the Flood HADR Simulation Framework. The system dynamically resolves and discovers required terrain (DEM) and hydrological datasets based on the selected Indian dam, reservoir, and river. We have verified this dynamic acquisition pipeline on both the Bhakra Dam test case and the Hirakud Dam generalization test. The automated pipeline successfully calculates the correct geographic domain and CRS, but hits authentication barriers when downloading from official Indian portals.

**Final Status:** `BLOCKED_NEEDS_SOURCE_ACCESS`

## 2. National Data Provider Architecture
To decouple simulation engines from Bhakra-specific data, we implemented an abstraction layer in `backend/app/services/government_data/interfaces.py`:
- `DEMProvider`: Interface for discovering and acquiring terrain datasets.
- `HydrologyProvider`: Interface for retrieving reservoir levels and river discharges.
- `DataAcquisitionManager`: Orchestrates the discovery of features (Dam, Reservoir, River), calculates the required spatial domain, determines the metric CRS, and queries the priority-ordered providers.

## 3. Official Data Sources
The architecture targets the following primary data sources:
- **Terrain:** ISRO Bhuvan CartoDEM (Primary), Survey of India, SRTM (Fallback).
- **Hydrology (National):** National Water Informatics Centre (NWIC), Central Water Commission (CWC).
- **Hydrology (Regional):** Bhakra Beas Management Board (BBMB) for Bhakra.

## 4. DEM Acquisition Workflow
1. **Feature Resolution:** Look up the Dam, corresponding Reservoir, and River from the local immutable `datasets/*.zip` inventory.
2. **Domain Calculation:** Calculate the union bounding box of these features and apply a 10 km spatial buffer.
3. **CRS Transformation:** Transform the local coordinates to WGS84 for tile querying.
4. **Tile Discovery:** The `BhuvanDEMProvider` identifies the required 1°×1° CartoDEM tiles.
5. **Metric CRS Selection:** The `DataAcquisitionManager` dynamically computes the correct UTM Zone (e.g., EPSG:32643 for Bhakra, EPSG:32644 for Hirakud) based on longitude.
6. **Download & Process:** (Blocked by CAPTCHA) Mosaic, reproject to the metric CRS, and crop to the domain.

## 5. Hydrology Acquisition Workflow
The system queries providers to find observed reservoir levels or river discharges. For the first `DAM_BREAK` simulation, only the initial reservoir water level is strictly required. The `DataAcquisitionManager` cycles through `BBMBProvider` (if applicable) and then `NWICProvider`.

## 6. Provider Priority Rules
- **Terrain:** Bhuvan > Survey of India > SRTM.
- **Hydrology:** BBMB (for Bhakra) > NWIC/CWC > State Departments.
The `DataAcquisitionManager` explicitly iterates providers in this priority order, stopping at the first successful data retrieval.

## 7. Data Normalization
Datasets are normalized into provider-independent Pydantic models (`TerrainDataset` and `HydrologyDataset`), standardizing coordinates, projections, and units (meters, m³/s) before handing them to the simulation engines.

## 8. Provenance Model
The normalized models preserve provenance explicitly:
- `source_provider` (e.g., "ISRO Bhuvan CartoDEM")
- `source_url`
- `acquisition_timestamp`
- `original_crs` vs `simulation_crs`

## 9. Bhakra Acquisition Result
- **Domain (WGS84):** Lon 76.26° to 76.86°, Lat 31.13° to 31.69°
- **Target CRS:** EPSG:32643
- **DEM Source:** ISRO Bhuvan CartoDEM (Blocked: CAPTCHA)
- **Hydrology Source:** BBMB / NWIC (Blocked: Auth/PDF)
- **Result:** `BLOCKED_NEEDS_SOURCE_ACCESS`

## 10. Second-Dam Generalization Test
To prove the architecture is not hardcoded, we ran the exact same workflow for **Hirakud Dam**:
- **Domain (WGS84):** Lon 83.39° to 84.14°, Lat 21.39° to 21.86°
- **Target CRS:** EPSG:32644 (Correctly shifted to UTM Zone 44N)
- **DEM Source:** ISRO Bhuvan CartoDEM (Blocked: CAPTCHA)
- **Hydrology Source:** NWIC (Blocked: Auth)
- **Result:** `BLOCKED_NEEDS_SOURCE_ACCESS`

The test proves the system is fully generalized.

## 11. Data Readiness Results
Both Bhakra and Hirakud report `BLOCKED_NEEDS_SOURCE_ACCESS`.

## 12. Downloaded Files
None. Automated download is blocked by authentication and CAPTCHAs.

## 13. Source URLs
- Bhuvan: `https://bhuvan-app1.nrsc.gov.in/2dresources/bhuvanstore.php`
- NWIC: `https://www.nwdp.nwic.gov.in/`
- BBMB: `https://bbmb.gov.in/data-reservoir.htm`

## 14. Validation Results
N/A (No files downloaded).

## 15. Blocking Issues
Automated, unauthenticated programmatic access to ISRO Bhuvan (requires login/CAPTCHA) and NWIC (requires API token) is unavailable. The system correctly halts rather than fabricating data.

## 16. Required Manual Actions
An authorized operator must manually:
1. Log into Bhuvan or USGS EarthExplorer and download the DEM tiles for the domains listed in Sections 9 and 10.
2. Reproject them to their respective target CRS (EPSG:32643 and EPSG:32644) and crop them.
3. Retrieve the observed reservoir water level from BBMB or CWC bulletins.

## 17. Recommended Next Phase
Once the data is manually acquired and placed into the system, proceed to Phase 3: Hydrodynamic Simulation Execution.

**Final Status:** `BLOCKED_NEEDS_SOURCE_ACCESS`
