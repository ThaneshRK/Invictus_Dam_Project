import os
import logging
from typing import Tuple, List, Optional
from meshkernel import MeshKernel, MakeGridParameters

logger = logging.getLogger(__name__)


class Delft3DMeshGenerator:
    """Generates a Delft3D-FM compliant unstructured computational mesh (_net.nc).
    
    Physical model: 2D depth-averaged D-Flow FM (Kmx=0).
    Mesh format: UGRID 1.0 convention NetCDF.
    """

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_rectangular_mesh(
        self,
        bounds: Tuple[float, float, float, float],
        resolution: float = 100.0,
        filename: str = "domain_net.nc",
        refinement_zones: Optional[List[dict]] = None
    ) -> str:
        """
        Generates a 2D rectangular unstructured grid over the given bounding box.

        Args:
            bounds: (xmin, ymin, xmax, ymax) in the project CRS
            resolution: Cell size in CRS units (e.g., meters)
            filename: Output filename
            refinement_zones: Optional list of dicts with 'bounds' and 'resolution'
                for local mesh refinement (e.g. near dam/breach)

        Returns:
            Absolute path to the generated _net.nc file
        """
        xmin, ymin, xmax, ymax = bounds

        # Validate bounds
        if xmax <= xmin or ymax <= ymin:
            raise ValueError(f"Invalid bounds: xmin={xmin}, ymin={ymin}, xmax={xmax}, ymax={ymax}")

        # Initialize MeshKernel
        mk = MeshKernel()

        # Define grid parameters
        make_grid_parameters = MakeGridParameters(
            angle=0.0,
            origin_x=xmin,
            origin_y=ymin,
            upper_right_x=xmax,
            upper_right_y=ymax,
            block_size_x=resolution,
            block_size_y=resolution
        )
        # MeshKernel >= 8 derives the grid from num_columns/num_rows (defaults are
        # 3x3 and upper_right is NOT used by mesh2d_make_rectangular_mesh), so we
        # compute the counts explicitly from the bounds and requested resolution.
        make_grid_parameters.num_columns = max(1, int(round((xmax - xmin) / resolution)))
        make_grid_parameters.num_rows = max(1, int(round((ymax - ymin) / resolution)))

        # Compute the regular unstructured Mesh2D
        mk.mesh2d_make_rectangular_mesh(make_grid_parameters)

        # Extract Mesh2D object
        m = mk.mesh2d_get()

        num_nodes = len(m.node_x)
        num_faces = len(m.face_x) if hasattr(m, 'face_x') and m.face_x is not None else 0
        logger.info(f"Generated mesh: {num_nodes} nodes, {num_faces} faces, resolution={resolution}")

        if num_nodes == 0:
            raise ValueError("Mesh generation produced zero nodes")

        # Write to UGRID NetCDF using xugrid
        import xugrid as xu
        import numpy as np

        nodes_per_face = m.nodes_per_face[0] if m.nodes_per_face.size > 0 else 4
        face_node_conn = m.face_nodes.reshape(-1, nodes_per_face)

        grid = xu.Ugrid2d(
            node_x=m.node_x,
            node_y=m.node_y,
            fill_value=-999,
            face_node_connectivity=face_node_conn
        )

        output_path = os.path.join(self.output_dir, filename)
        ds = grid.to_dataset()

        # Add UGRID conventions and metadata expected by dflowfm
        ds.attrs["Conventions"] = "CF-1.6 UGRID-1.0"
        ds.attrs["institution"] = "Flood HADR Framework"

        ds.to_netcdf(output_path)

        logger.info(f"Mesh written to {output_path}")
        return output_path

    def get_mesh_info(self, mesh_path: str) -> dict:
        """Returns mesh statistics for validation and metadata."""
        import xarray as xr
        ds = xr.open_dataset(mesh_path)
        info = {
            "file": mesh_path,
            "variables": list(ds.variables.keys()),
            "dimensions": dict(ds.dims),
            "attributes": dict(ds.attrs)
        }
        ds.close()
        return info
