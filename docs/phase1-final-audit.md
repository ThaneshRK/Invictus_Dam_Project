# Phase 1 Final Read-Only Audit

## Selected Test Entity
**Dam**: Bhakra Dam 
**Dam ID**: `2a508b04-faec-4f93-81d1-bfd81d2c8366`

---

## 1. How was Dam → Reservoir determined?
**PASS**
Determined dynamically via a backend spatial query during the ingestion pipeline. The `run_government_ingestion.py` script ran a PostGIS intersection mapping between the dam point coordinates and the reservoir multipolygons.
**Database record identified**: Reservoir ID `e8193d97-83e9-411e-a4ef-0e541985c12a`.

## 2. How was Dam → River determined?
**PASS**
Determined dynamically via a spatial proximity query (`SPATIAL_DWITHIN`) matching the dam geometry to the nearest river geometry within a defined radius.
**Database record identified**: River ID `9f86e937-9231-4d04-b815-ff0913c80356`.

## 3. What match_method/match_status/confidence is stored?
**PASS**
- **Reservoir**: `match_method: SPATIAL_DWITHIN`, `confidence: 0.8`
- **River**: `match_method: SPATIAL_DWITHIN`, `confidence: 0.7`
These are properly persisted in the `DamRelationship` table.

## 4. Are the reservoir and river actually persisted on the Project?
**PASS**
Yes. Through `ProjectWizard.tsx`, when the user selects a Dam, the frontend queries `/government/dams/{id}/readiness`. The frontend extracts `target_id` from the resulting relationship JSON payload and actively sends them inside the PUT request to `/projects/{id}`, persisting `selected_reservoir_id` and `selected_river_id` to the database.

## 5. Is the Study Area persisted as PostGIS geometry?
**PASS**
Yes. The Leaflet map captures the raw polygon coordinates within the `onCreated` trigger and transmits the resulting GeoJSON dictionary to the project database where SQLAlchemy (via geoalchemy2) inserts it as a geometry.

## 6. Does the DEM actually cover the Study Area?
**NOT TESTABLE**
The logic for bounds checking exists and is enforced by `SimulationInputContext`. However, a real DEM dataset covering Bhakra Dam is currently **unavailable** in the project repository to perform an actual pixel-to-geometry test without faking data. The user must manually upload a valid `.tif` through the Data Management UI.

## 7. Does the hydrological dataset actually belong to the project/scenario?
**NOT TESTABLE**
The linkage and validation constraints exist (e.g. checking for `timestamp` and `value` columns and refusing execution if missing for `WATER_RELEASE` scenarios). However, a real hydrological `.csv` corresponding to Bhakra Dam is **unavailable** in the standard dataset package.

## 8. Does SimulationInputContext retrieve these actual records?
**PASS**
Yes. Inside `backend/app/core/simulation_context.py`, the system explicitly executes `await db.get(GovernmentDam, project.selected_dam_id)`, etc. It fully hydrates the ORM models rather than merely doing superficial string existence checks.

## 9. Does /scenarios/{id}/validate use those records rather than only checking whether IDs are non-null?
**PASS**
Yes. By delegating directly to `SimulationInputContext.build(...)`, the validation endpoint ensures that a `404 Not Found` is thrown if the IDs point to non-existent rows, or `400 Bad Request` if topological mismatches occur between the fully retrieved records.

## 10. Does Start Simulation refuse to create a job when validation fails?
**PASS**
Yes. In `ScenarioBuilder.tsx`, the UI explicitly halts execution (`return;`) within the `catch` block if `/validate` throws an `HTTPException`. No job is entered into the queue.

---

## Conclusion
- **Worker Code**: No modifications were made to SPH2D, SPH3D, Delft3D, or D-Flow FM.
- **Status**: The physical topology of Phase 1 is validated and successfully integrates dynamically loaded spatial data without hardcoding.
