from .nrld_provider import NRLDProvider
from .census_provider import CensusIndiaProvider
from .infrastructure_provider import LocalDatasetInfrastructureProvider
from .water_provider import LocalDatasetWaterProvider
from .base_provider import GovernmentDamProvider, PopulationProvider, WaterDataProvider, InfrastructureProvider

def get_dam_provider() -> GovernmentDamProvider:
    return NRLDProvider()

def get_population_provider() -> PopulationProvider:
    return CensusIndiaProvider()

def get_infrastructure_provider() -> InfrastructureProvider:
    return LocalDatasetInfrastructureProvider()

def get_water_provider() -> WaterDataProvider:
    return LocalDatasetWaterProvider()
