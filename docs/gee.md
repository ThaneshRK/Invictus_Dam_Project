# Google Earth Engine (GEE) Integration

Phase 11 connects the framework to GEE to download and classify Sentinel-1 Synthetic Aperture Radar (SAR) imagery, generating ground-truth observations to validate our simulations against.

## Authentication
By default, the backend searches for `earthengine` credentials in the host system.

## Test Fixtures
If GEE is unavailable (e.g. CI environments, local prototyping without service accounts), `GEEService.analyze_flood_extent()` intercepts the authorization error and immediately returns a valid JSON payload containing mocked output paths. These are strictly flagged as `"type": "TEST DATA"` to ensure academic transparency.
