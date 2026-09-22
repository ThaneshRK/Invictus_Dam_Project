import os
import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.windows import Window
import geopandas as gpd
import numpy as np
from scipy import ndimage
from shapely.geometry import shape

class GISService:
    @staticmethod
    def normalize_crs(gdf: gpd.GeoDataFrame, target_crs: str = "EPSG:4326") -> gpd.GeoDataFrame:
        if not gdf.crs:
            gdf.set_crs(target_crs, inplace=True)
        elif gdf.crs.to_string() != target_crs:
            gdf = gdf.to_crs(target_crs)
        return gdf

    @staticmethod
    def validate_dem(file_path: str) -> dict:
        with rasterio.open(file_path) as src:
            return {
                "crs": src.crs.to_string() if src.crs else None,
                "resolution": src.res,
                "bounds": src.bounds,
                "nodata": src.nodata
            }

    @staticmethod
    def clip_dem(input_path: str, output_path: str, shapes: list, crop: bool = True):
        with rasterio.open(input_path) as src:
            out_image, out_transform = mask(src, shapes, crop=crop)
            out_meta = src.meta.copy()
            out_meta.update({
                "driver": "GTiff",
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform
            })
            
            with rasterio.open(output_path, "w", **out_meta) as dest:
                dest.write(out_image)

    @staticmethod
    def handle_nodata(input_path: str, output_path: str, new_nodata_val: float):
        with rasterio.open(input_path) as src:
            meta = src.meta.copy()
            meta.update(nodata=new_nodata_val)
            
            with rasterio.open(output_path, "w", **meta) as dest:
                # Windowed processing for large rasters
                for ji, window in src.block_windows(1):
                    data = src.read(1, window=window)
                    # Replace existing nodata or nans if any
                    if src.nodata is not None:
                        data[data == src.nodata] = new_nodata_val
                    data[np.isnan(data)] = new_nodata_val
                    dest.write(data, 1, window=window)

    @staticmethod
    def resample_dem(input_path: str, output_path: str, scale_factor: float = 2.0):
        with rasterio.open(input_path) as src:
            # resample data to target shape
            t_height = int(src.height * scale_factor)
            t_width = int(src.width * scale_factor)
            
            data = src.read(
                out_shape=(src.count, t_height, t_width),
                resampling=Resampling.bilinear
            )

            # scale image transform
            transform = src.transform * src.transform.scale(
                (src.width / data.shape[-1]),
                (src.height / data.shape[-2])
            )

            meta = src.meta.copy()
            meta.update({
                "transform": transform,
                "width": t_width,
                "height": t_height
            })
            
            with rasterio.open(output_path, "w", **meta) as dest:
                dest.write(data)

    @staticmethod
    def calculate_slope_aspect(input_path: str, slope_path: str, aspect_path: str):
        """Calculates slope and aspect using scipy convolutions. Modular placeholder for hydrology."""
        with rasterio.open(input_path) as src:
            data = src.read(1)
            # Simple gradient utilizing numpy/scipy
            dx, dy = np.gradient(data, src.res[0], src.res[1])
            
            # Slope calculation
            slope = np.degrees(np.arctan(np.sqrt(dx**2 + dy**2)))
            
            # Aspect calculation
            aspect = np.degrees(np.arctan2(-dy, dx))
            aspect = np.where(aspect < 0, aspect + 360, aspect)
            
            meta = src.meta.copy()
            meta.update(dtype=rasterio.float32)
            
            with rasterio.open(slope_path, "w", **meta) as dest:
                dest.write(slope.astype(rasterio.float32), 1)
                
            with rasterio.open(aspect_path, "w", **meta) as dest:
                dest.write(aspect.astype(rasterio.float32), 1)

    @staticmethod
    def prepare_river_geometry(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Extract lines, calculate simple lengths if necessary."""
        return GISService.normalize_crs(gdf)

    @staticmethod
    def prepare_dam_geometry(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Extract points or polygons representing dams."""
        return GISService.normalize_crs(gdf)

    @staticmethod
    def prepare_blockage_geometry(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        return GISService.normalize_crs(gdf)
