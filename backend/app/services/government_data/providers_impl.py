import os
import asyncio
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import urllib.request
import urllib.error

from app.services.government_data.interfaces import DEMProvider, TerrainDataset, HydrologyProvider, HydrologyDataset

def get_fixtures_dir() -> Path:
    """Finds the path to data/fixtures/government directory."""
    candidates = [
        Path("/home/agent001/Desktop/project/sih/dam-project/data/fixtures/government"),
        Path(__file__).resolve().parents[4] / "data" / "fixtures" / "government",
        Path(__file__).resolve().parents[3] / "data" / "fixtures" / "government",
        Path("data/fixtures/government"),
        Path("backend/data/fixtures/government"),
    ]
    for p in candidates:
        if p.exists() and (p / "manifest.json").exists():
            return p.resolve()
    # Fallback to root path
    return Path("/home/agent001/Desktop/project/sih/dam-project/data/fixtures/government")


class OpenTopographyDEMProvider(DEMProvider):
    """
    OpenTopography DEM Provider for downloading real SRTMGL1 GeoTIFF rasters.
    NO synthetic fallback terrain is used.
    """
    def get_provider_name(self) -> str:
        return "OpenTopography"

    async def discover_dem(self, bbox_wgs84: Tuple[float, float, float, float]) -> Dict[str, Any]:
        min_lon, min_lat, max_lon, max_lat = bbox_wgs84
        api_key = os.getenv("OPENTOPOGRAPHY_API_KEY", "")
        return {
            "provider": self.get_provider_name(),
            "dataset": "SRTMGL1",
            "bbox": [min_lon, min_lat, max_lon, max_lat],
            "resolution": "30m",
            "api_endpoint": "https://portal.opentopography.org/API/globaldem",
            "api_key_configured": bool(api_key),
            "status": "DISCOVERED"
        }

    async def acquire_dem(self, bbox_wgs84: Tuple[float, float, float, float], target_crs: str, output_dir: str) -> TerrainDataset:
        min_lon, min_lat, max_lon, max_lat = bbox_wgs84
        api_key = os.getenv("OPENTOPOGRAPHY_API_KEY", "")
        
        url = (
            f"https://portal.opentopography.org/API/globaldem?"
            f"demtype=SRTMGL1&south={min_lat}&north={max_lat}&west={min_lon}&east={max_lon}"
            f"&outputFormat=GTiff"
        )
        if api_key:
            url += f"&API_Key={api_key}"

        out_path = Path(output_dir) / f"opentopography_srtmgl1_{min_lat:.2f}_{min_lon:.2f}.tif"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Attempt real download
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            def _download():
                with urllib.request.urlopen(req, timeout=30) as resp, open(out_path, 'wb') as f:
                    f.write(resp.read())
            
            await asyncio.to_thread(_download)

            if not out_path.exists() or out_path.stat().st_size < 1000:
                raise Exception("Downloaded file is empty or invalid.")

            return TerrainDataset(
                source_provider="OpenTopography",
                source_dataset="SRTMGL1",
                source_url=url,
                acquisition_timestamp=datetime.now(timezone.utc).isoformat(),
                original_crs="EPSG:4326",
                simulation_crs=target_crs,
                resolution=30.0,
                bounds=bbox_wgs84,
                vertical_units="m",
                nodata=-9999.0,
                local_file=str(out_path)
            )

        except Exception as e:
            # Raise strict error without fallback synthetic DEM
            raise Exception(f"DEM_STATUS = BLOCKED: OpenTopography acquisition failed ({str(e)}). Synthetic DEM is disabled.")


class GovernmentStaticHydrologyProvider(HydrologyProvider):
    """
    HydrologyProvider implementation loading real government-sourced static fixtures
    for the 5 Indian Dam-Reservoir-River systems.
    """

    def get_provider_name(self) -> str:
        return "Government Static Fixture Hydrology Provider"

    @staticmethod
    def feet_to_meters(ft: float) -> float:
        return round(ft * 0.3048, 5)

    @staticmethod
    def cusecs_to_cms(cusecs: float) -> float:
        return round(cusecs * 0.028316846592, 5)

    @staticmethod
    def mcm_to_m3(mcm: float) -> float:
        return round(mcm * 1000000.0, 2)

    def _match_dam_id(self, name: str) -> Optional[str]:
        n = name.lower()
        if "bhakra" in n or "gobind" in n or "satluj" in n or "sutlej" in n:
            return "bhakra"
        if "tehri" in n or "bhagirathi" in n:
            return "tehri"
        if "hirakud" in n or "mahanadi" in n:
            return "hirakud"
        if "sardar" in n or "sarovar" in n or "narmada" in n:
            return "sardar_sarovar"
        if "mettur" in n or "stanley" in n or "cauvery" in n:
            return "mettur"
        return None

    def get_system_fixture(self, dam_id_or_name: str) -> Optional[Dict[str, Any]]:
        dam_id = self._match_dam_id(dam_id_or_name) or dam_id_or_name.lower().replace(" ", "_")
        fixtures_dir = get_fixtures_dir()
        
        dam_file = fixtures_dir / "dams" / f"{dam_id}.json"
        res_file = fixtures_dir / "reservoirs" / f"{dam_id}.json"
        hydro_file = fixtures_dir / "hydrology" / f"{dam_id}.json"

        if not dam_file.exists() or not hydro_file.exists():
            return None

        with open(dam_file, "r") as f:
            dam_data = json.load(f)
        with open(res_file, "r") as f:
            res_data = json.load(f)
        with open(hydro_file, "r") as f:
            hydro_data = json.load(f)

        # Match river file
        river_name = dam_data.get("river_name", "")
        river_file = fixtures_dir / "rivers" / f"{river_name.lower()}.json"
        river_data = {}
        if river_file.exists():
            with open(river_file, "r") as f:
                river_data = json.load(f)

        return {
            "dam": dam_data,
            "reservoir": res_data,
            "river": river_data,
            "hydrology": hydro_data
        }

    def get_all_systems(self) -> List[Dict[str, Any]]:
        fixtures_dir = get_fixtures_dir()
        manifest_file = fixtures_dir / "manifest.json"
        if manifest_file.exists():
            with open(manifest_file, "r") as f:
                manifest = json.load(f)
                systems = []
                for sys_info in manifest.get("systems", []):
                    data = self.get_system_fixture(sys_info["id"])
                    if data:
                        systems.append(data)
                return systems
        return []

    async def get_reservoir_level(self, reservoir_name: str, dam_name: str, timestamp: Optional[datetime] = None) -> Optional[HydrologyDataset]:
        fixture = self.get_system_fixture(dam_name) or self.get_system_fixture(reservoir_name)
        if not fixture:
            return None

        hydro = fixture["hydrology"]
        obs_list = hydro.get("observations", [])
        if not obs_list:
            return None

        obs = obs_list[0]
        wl = obs.get("water_level")
        if not wl:
            return None

        prov = obs.get("provenance", {})
        return HydrologyDataset(
            source_provider=hydro.get("source", {}).get("provider", "GOVERNMENT_STATIC_FIXTURE"),
            source_dataset=prov.get("source_dataset", "Government Static Fixture"),
            station_id=fixture["dam"]["id"],
            station_name=fixture["dam"]["dam_name"],
            reservoir=fixture["reservoir"]["reservoir_name"],
            river=fixture["dam"]["river_name"],
            parameter="reservoir_level",
            units_normalized=wl.get("normalized_unit", "m"),
            timestamp=obs.get("timestamp", datetime.now(timezone.utc).isoformat()),
            value=wl.get("normalized_value"),
            source_url=prov.get("source_url", ""),
            acquisition_timestamp=prov.get("retrieved_timestamp", datetime.now(timezone.utc).isoformat()),
            source_agency=prov.get("source_agency"),
            observation_type=obs.get("observation_type", "OBSERVATION"),
            original_value=wl.get("value"),
            original_unit=wl.get("unit"),
            normalized_value=wl.get("normalized_value"),
            normalized_unit=wl.get("normalized_unit"),
            is_live=False,
            is_synthetic=False,
            source_type=prov.get("source_type", "GOVERNMENT_STATIC_FIXTURE"),
            availability=wl.get("availability", "AVAILABLE")
        )

    async def get_river_discharge(self, river_name: str, coordinates: Tuple[float, float], timestamp: Optional[datetime] = None) -> Optional[HydrologyDataset]:
        fixture = self.get_system_fixture(river_name)
        if not fixture:
            return None

        hydro = fixture["hydrology"]
        obs_list = hydro.get("observations", [])
        if not obs_list:
            return None

        obs = obs_list[0]
        outflow = obs.get("outflow")
        if not outflow or outflow.get("value") is None:
            # Missing discharge - return dataset marked NOT_PROVIDED
            prov = obs.get("provenance", {})
            return HydrologyDataset(
                source_provider=hydro.get("source", {}).get("provider", "GOVERNMENT_STATIC_FIXTURE"),
                source_dataset=prov.get("source_dataset", "Government Static Fixture"),
                station_id=fixture["dam"]["id"],
                station_name=fixture["dam"]["dam_name"],
                reservoir=fixture["reservoir"]["reservoir_name"],
                river=fixture["dam"]["river_name"],
                parameter="discharge",
                units_normalized="m3/s",
                timestamp=obs.get("timestamp", datetime.now(timezone.utc).isoformat()),
                value=None,
                source_url=prov.get("source_url", ""),
                acquisition_timestamp=prov.get("retrieved_timestamp", datetime.now(timezone.utc).isoformat()),
                source_agency=prov.get("source_agency"),
                observation_type=obs.get("observation_type", "OBSERVATION"),
                original_value=None,
                original_unit=None,
                normalized_value=None,
                normalized_unit="m3/s",
                is_live=False,
                is_synthetic=False,
                source_type=prov.get("source_type", "GOVERNMENT_STATIC_FIXTURE"),
                availability="NOT_PROVIDED"
            )

        prov = obs.get("provenance", {})
        return HydrologyDataset(
            source_provider=hydro.get("source", {}).get("provider", "GOVERNMENT_STATIC_FIXTURE"),
            source_dataset=prov.get("source_dataset", "Government Static Fixture"),
            station_id=fixture["dam"]["id"],
            station_name=fixture["dam"]["dam_name"],
            reservoir=fixture["reservoir"]["reservoir_name"],
            river=fixture["dam"]["river_name"],
            parameter="discharge",
            units_normalized=outflow.get("normalized_unit", "m3/s"),
            timestamp=obs.get("timestamp", datetime.now(timezone.utc).isoformat()),
            value=outflow.get("normalized_value"),
            source_url=prov.get("source_url", ""),
            acquisition_timestamp=prov.get("retrieved_timestamp", datetime.now(timezone.utc).isoformat()),
            source_agency=prov.get("source_agency"),
            observation_type=obs.get("observation_type", "OBSERVATION"),
            original_value=outflow.get("value"),
            original_unit=outflow.get("unit"),
            normalized_value=outflow.get("normalized_value"),
            normalized_unit=outflow.get("normalized_unit"),
            is_live=False,
            is_synthetic=False,
            source_type=prov.get("source_type", "GOVERNMENT_STATIC_FIXTURE"),
            availability=outflow.get("availability", "AVAILABLE")
        )


class BhuvanDEMProvider(DEMProvider):
    def get_provider_name(self) -> str:
        return "ISRO Bhuvan CartoDEM"
        
    async def discover_dem(self, bbox_wgs84: Tuple[float, float, float, float]) -> Dict[str, Any]:
        min_lon, min_lat, max_lon, max_lat = bbox_wgs84
        tiles = []
        for lat in range(int(min_lat), int(max_lat) + 1):
            for lon in range(int(min_lon), int(max_lon) + 1):
                lat_str = f"N{lat:02d}" if lat >= 0 else f"S{abs(lat):02d}"
                lon_str = f"E{lon:03d}" if lon >= 0 else f"W{abs(lon):03d}"
                tiles.append(f"{lat_str}{lon_str}")
                
        return {
            "provider": self.get_provider_name(),
            "status": "DISCOVERED",
            "tiles_required": tiles,
            "resolution": "30m",
            "auth_required": True,
            "download_url": "https://bhuvan-app1.nrsc.gov.in/2dresources/bhuvanstore.php"
        }

    async def acquire_dem(self, bbox_wgs84: Tuple[float, float, float, float], target_crs: str, output_dir: str) -> TerrainDataset:
        discovery = await self.discover_dem(bbox_wgs84)
        if discovery["auth_required"]:
            raise Exception("BLOCKED_NEEDS_SOURCE_ACCESS: Bhuvan CartoDEM requires authenticated manual download via CAPTCHA. Automated download is unavailable.")


class NWICProvider(HydrologyProvider):
    def get_provider_name(self) -> str:
        return "National Water Informatics Centre (NWIC)"
        
    async def get_reservoir_level(self, reservoir_name: str, dam_name: str, timestamp: Optional[datetime] = None) -> Optional[HydrologyDataset]:
        raise Exception(f"BLOCKED_NEEDS_SOURCE_ACCESS: NWIC API requires authorization token for reservoir {reservoir_name}.")
        
    async def get_river_discharge(self, river_name: str, coordinates: Tuple[float, float], timestamp: Optional[datetime] = None) -> Optional[HydrologyDataset]:
        raise Exception(f"BLOCKED_NEEDS_SOURCE_ACCESS: NWIC API requires authorization token for river {river_name}.")


class BBMBProvider(HydrologyProvider):
    def get_provider_name(self) -> str:
        return "Bhakra Beas Management Board (BBMB)"
        
    async def get_reservoir_level(self, reservoir_name: str, dam_name: str, timestamp: Optional[datetime] = None) -> Optional[HydrologyDataset]:
        if "Bhakra" in dam_name or "Govind" in reservoir_name:
            raise Exception("BLOCKED_NEEDS_SOURCE_ACCESS: BBMB daily bulletin is published as PDF/HTML without an automated machine-readable API.")
        return None
        
    async def get_river_discharge(self, river_name: str, coordinates: Tuple[float, float], timestamp: Optional[datetime] = None) -> Optional[HydrologyDataset]:
        return None
