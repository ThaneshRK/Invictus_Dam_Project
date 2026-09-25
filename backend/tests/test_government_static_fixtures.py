import pytest
import pytest_asyncio
import asyncio
from pathlib import Path
import json

from app.services.government_data.providers_impl import GovernmentStaticHydrologyProvider, OpenTopographyDEMProvider
from app.services.government_data.interfaces import HydrologyDataset

pytestmark = pytest.mark.asyncio

@pytest.fixture
def provider():
    return GovernmentStaticHydrologyProvider()

@pytest.fixture
def dem_provider():
    return OpenTopographyDEMProvider()

async def test_all_five_systems_loaded(provider):
    systems = provider.get_all_systems()
    assert len(systems) == 5
    
    ids = [sys["dam"]["id"] for sys in systems]
    assert "bhakra" in ids
    assert "tehri" in ids
    assert "hirakud" in ids
    assert "sardar_sarovar" in ids
    assert "mettur" in ids

async def test_bhakra_system_provenance_and_units(provider):
    sys = provider.get_system_fixture("bhakra")
    assert sys is not None
    
    dam = sys["dam"]
    res = sys["reservoir"]
    river = sys["river"]
    hydro = sys["hydrology"]
    
    assert dam["dam_name"] == "Bhakra Dam"
    assert res["reservoir_name"] == "Gobind Sagar"
    assert river["river_name"] == "Sutlej"
    assert dam["source"]["source_type"] == "GOVERNMENT_STATIC_FIXTURE"
    assert dam["source"]["is_live"] is False
    assert dam["source"]["is_synthetic"] is False
    
    obs = hydro["observations"][0]
    assert obs["observation_type"] == "OBSERVATION"
    assert obs["water_level"]["value"] == 1642.2
    assert obs["water_level"]["unit"] == "ft"
    assert obs["water_level"]["normalized_unit"] == "m"
    assert round(obs["water_level"]["normalized_value"], 2) == 500.54
    
    assert obs["inflow"]["value"] == 17628
    assert obs["inflow"]["unit"] == "cusecs"
    assert obs["inflow"]["normalized_unit"] == "m3/s"
    
    assert obs["outflow"]["value"] == 27613
    assert obs["outflow"]["unit"] == "cusecs"
    assert obs["outflow"]["normalized_unit"] == "m3/s"

async def test_tehri_forecast_type(provider):
    sys = provider.get_system_fixture("tehri")
    assert sys is not None
    
    obs = sys["hydrology"]["observations"][0]
    assert obs["observation_type"] == "FORECAST"
    assert obs["provenance"]["is_live"] is False
    assert obs["provenance"]["is_synthetic"] is False
    assert obs["water_level"]["value"] == 825.960
    assert obs["water_level"]["unit"] == "m"
    assert obs["inflow"]["value"] == 428.550
    assert obs["outflow"]["value"] == 450.00

async def test_hirakud_missing_hydrology_handling(provider):
    sys = provider.get_system_fixture("hirakud")
    assert sys is not None
    
    obs = sys["hydrology"]["observations"][0]
    assert obs["observation_type"] == "HISTORICAL_REFERENCE"
    assert obs["water_level"]["value"] == 187.28
    
    # Must be null and NOT_PROVIDED
    assert obs["inflow"] is None
    assert obs["inflow_availability"] == "NOT_PROVIDED"
    assert obs["outflow"] is None
    assert obs["outflow_availability"] == "NOT_PROVIDED"
    
    # Provider discharge query must return NOT_PROVIDED dataset without throwing error
    ds = await provider.get_river_discharge("Mahanadi", (83.87, 21.57))
    assert ds is not None
    assert ds.availability == "NOT_PROVIDED"
    assert ds.value is None

async def test_sardar_sarovar_system(provider):
    sys = provider.get_system_fixture("sardar_sarovar")
    assert sys is not None
    
    dam = sys["dam"]
    assert dam["dam_name"] == "Sardar Sarovar Dam"
    assert dam["river_name"] == "Narmada"
    
    obs = sys["hydrology"]["observations"][0]
    assert obs["observation_type"] == "HISTORICAL_REFERENCE"
    assert obs["water_level"]["value"] == 132.50
    assert obs["storage"]["value"] == 1817.55
    assert obs["storage"]["unit"] == "MCM"
    assert obs["storage"]["normalized_value"] == 1817550000.0

async def test_mettur_system(provider):
    sys = provider.get_system_fixture("mettur")
    assert sys is not None
    
    dam = sys["dam"]
    assert dam["dam_name"] == "Mettur Dam"
    assert dam["reservoir_name"] == "Stanley Reservoir"
    assert dam["river_name"] == "Cauvery"
    
    obs = sys["hydrology"]["observations"][0]
    assert obs["water_level"]["value"] == 240.79
    assert obs["storage"]["value"] == 204.0
    assert obs["storage"]["unit"] == "MCM"

async def test_provider_get_reservoir_level(provider):
    dataset = await provider.get_reservoir_level("Gobind Sagar", "Bhakra Dam")
    assert dataset is not None
    assert dataset.parameter == "reservoir_level"
    assert dataset.original_value == 1642.2
    assert dataset.original_unit == "ft"
    assert round(dataset.normalized_value, 2) == 500.54
    assert dataset.is_live is False
    assert dataset.is_synthetic is False
    assert dataset.source_agency == "Bhakra Beas Management Board (BBMB)"

async def test_opentopography_provider_discovery(dem_provider):
    discovery = await dem_provider.discover_dem((76.0, 31.0, 77.0, 32.0))
    assert discovery["provider"] == "OpenTopography"
    assert discovery["dataset"] == "SRTMGL1"
    assert discovery["status"] == "DISCOVERED"

async def test_opentopography_no_synthetic_fallback(dem_provider, tmp_path):
    # Without valid external network/API key, should fail cleanly with BLOCKED status, never synthetic
    with pytest.raises(Exception) as exc_info:
        await dem_provider.acquire_dem((76.0, 31.0, 77.0, 32.0), "EPSG:32643", str(tmp_path))
    assert "DEM_STATUS = BLOCKED" in str(exc_info.value)
