# Idukki Dam / Periyar River Demonstration

This directory contains the reproducible configuration for running the complete Flood HADR pipeline for the **Idukki Dam** in Kerala, India.

## Geography & Data Sources
- **River**: Periyar River, Kerala
- **Dam**: Idukki Arch Dam (Double Curvature Arch)
- **DEM Source**: NASA SRTM 30m (Public Domain) via [USGS EarthExplorer](https://earthexplorer.usgs.gov/)
- **Infrastructure Source**: OpenStreetMap (ODbL)

## Execution Instructions
1. **DATA INGESTION**:
   Download the SRTM DEM covering `9.84 N, 76.97 E` and upload it via the Dashboard (`POST /api/v1/datasets`).
2. **PREPROCESSING**:
   The system will automatically extract the bounds and reproject to `EPSG:32643` (UTM Zone 43N).
3. **SCENARIO**:
   The `config.json` assumes a catastrophic full-arch failure, unleashing the ~2 billion cubic meter reservoir. Submit this payload to `/api/v1/scenarios`.
4. **SIMULATION**:
   Trigger the job using `SPH`. If `Delft3D` is installed, trigger a comparative run.
5. **GEE VALIDATION**:
   If Sentinel-1 SAR imagery is available post-event, the GEE service will extract it. (If credentials are not mounted, the system provides fixture maps).
6. **HADR EXPOSURE**:
   The `HADRService` will intersect the resulting GeoTIFF flood depths against OSM building footprints and road networks.

## Missing Data Handling
To strictly adhere to requirements: we **do not fabricate missing geometry**. If the user does not supply the actual SRTM Tiff to the API, the scenario validator will reject execution. If Delft3D is not installed on your system, the Adapter simulates completion and provides a `TEST FIXTURE` payload rather than faking actual `.map` files.
