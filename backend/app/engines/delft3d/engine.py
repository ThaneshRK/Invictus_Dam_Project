"""
Delft3D-FM Engine Adapter.

Orchestrates: validate → build workspace → execute dflowfm → parse results.

Physical model: 2D depth-averaged D-Flow FM (Saint-Venant / Shallow Water Equations).
This is NOT a vertically-resolved 3D solver. Kmx=0 in all configurations.
The installed D-Flow FM Version is 1.2.184.

Supported scenarios:
  - DAM_BREAK: Native ST_DAMBREAK structure with Verheij-van der Knaap breach growth
  - WATER_RELEASE: Discharge boundary with Q(t) time series
  - RIVER_BLOCKAGE: Elevated terrain blockage + timed dambreak failure
"""
import os
import logging
from typing import Dict, Any, Optional

from app.engines.base import SimulationEngine
from app.engines.delft3d.executor import HostDelft3DExecutor, DockerDelft3DExecutor
from app.engines.delft3d.builder import Delft3DModelBuilder
from app.engines.delft3d.parser import Delft3DResultParser
from app.core.config import settings

logger = logging.getLogger(__name__)


class Delft3DEngine(SimulationEngine):
    """
    Adapter for executing real Delft3D-FM hydrodynamic simulations.

    This engine:
    1. Validates that the dflowfm binary is available
    2. Builds a complete simulation workspace (mesh, terrain, boundaries, MDU)
    3. Executes dflowfm as a subprocess
    4. Parses NetCDF output
    5. Returns results in the common format
    """

    def __init__(self, context: Any, workspace_dir: Optional[str] = None):
        super().__init__(context)
        self.workspace_root = workspace_dir or settings.DELFT3D_WORKSPACE_ROOT
        self.executor = None
        self.builder = None
        self.parser = None
        self._logs = ""

    def validate(self) -> bool:
        """Validates that the Delft3D environment is properly configured."""
        if not settings.DELFT3D_ENABLED:
            self.error_message = "Delft3D engine is not enabled. Set DELFT3D_ENABLED=True."
            return False

        # Check that the run script exists
        run_script = os.path.join(settings.DELFT3D_INSTALL_DIR, "bin", "run_dflowfm.sh")
        if settings.DELFT3D_EXECUTION_MODE == "host" and not os.path.exists(run_script):
            self.error_message = f"run_dflowfm.sh not found at {run_script}"
            return False

        st = self.context.scenario.scenario_type
        scenario_type = st.value if hasattr(st, 'value') else str(st)

        valid_types = ["DAM_BREAK", "WATER_RELEASE", "CONTROLLED_RELEASE", "RIVER_BLOCKAGE"]
        if scenario_type.upper() not in valid_types:
            self.error_message = f"Unknown scenario type: {scenario_type}. Valid: {valid_types}"
            return False

        return True

    def prepare(self) -> None:
        """Creates the simulation workspace, generates mesh, MDU, and all forcing files."""
        self.status = "PREPARING"

        try:
            self.builder = Delft3DModelBuilder(
                workspace_root=self.workspace_root,
                simulation_id=self.simulation_id,
                context=self.context
            )

            mdu_filename = self.builder.build()

            # Select executor based on configuration
            if settings.DELFT3D_EXECUTION_MODE == "docker":
                self.executor = DockerDelft3DExecutor(self.builder.workspace_path, mdu_filename)
            else:
                self.executor = HostDelft3DExecutor(self.builder.workspace_path, mdu_filename)

            self.status = "PREPARED"
            logger.info(f"Delft3D workspace prepared at {self.builder.workspace_path}")

        except Exception as e:
            self.status = "FAILED"
            self.error_message = f"Failed to prepare Delft3D workspace: {e}"
            logger.exception("Delft3D prepare failed")

    def run(self) -> None:
        """Executes the dflowfm simulation (blocking)."""
        if self.status == "FAILED":
            return

        if self.executor is None:
            self.status = "FAILED"
            self.error_message = "No executor available — prepare() was not called or failed"
            return

        self.status = "RUNNING"

        try:
            self.executor.start()

            if self.executor.exit_code is not None and self.executor.exit_code != 0:
                self.status = "FAILED"
                self.error_message = self.executor.error_message or "Failed to start dflowfm"
                return

            # Block until completion or timeout
            exit_code = self.executor.wait(timeout=settings.DELFT3D_TIMEOUT_SECONDS)

            # Capture logs
            self._logs = self.executor.get_logs()

            if exit_code == 0:
                self.status = "COMPLETED"
                logger.info("Delft3D simulation completed successfully")
            else:
                self.status = "FAILED"
                self.error_message = self.executor.error_message or f"dflowfm exited with code {exit_code}"
                logger.error(f"Delft3D simulation failed: {self.error_message}")

        except Exception as e:
            self.status = "FAILED"
            self.error_message = f"Delft3D execution error: {e}"
            logger.exception("Delft3D run failed")

    def get_status(self) -> Dict[str, Any]:
        """Returns the current status of the simulation."""
        progress = 0.0
        if self.status == "COMPLETED":
            progress = 100.0
        elif self.status == "RUNNING" and self.executor:
            # Check if output files are being produced
            output_dir = os.path.join(self.builder.workspace_path, "output") if self.builder else ""
            if output_dir and os.path.exists(output_dir):
                import glob
                nc_files = glob.glob(os.path.join(output_dir, "*.nc"))
                if nc_files:
                    progress = 50.0  # At least some output is being generated

        return {
            "status": self.status,
            "progress_percent": progress,
            "error": self.error_message,
            "workspace": self.builder.workspace_path if self.builder else None
        }

    def cancel(self) -> None:
        """Cancels the running simulation."""
        if self.executor:
            self.executor.cancel()
        self.status = "CANCELLED"

    def load_results(self) -> Dict[str, Any]:
        """Parses the dflowfm NetCDF output into the common result format."""
        if self.status != "COMPLETED":
            return {}

        if not self.builder:
            return {}

        self.parser = Delft3DResultParser(self.builder.workspace_path)

        try:
            result_meta = self.parser.parse()

            return {
                "engine": "delft3d",
                "engine_version": "D-Flow FM 1.2.184",
                "physical_model": "2D depth-averaged (Kmx=0)",
                "crs": result_meta.get("crs", "Unknown"),
                "bounds": result_meta.get("bounds"),
                "max_depth": result_meta.get("max_water_depth"),
                "max_water_depth": result_meta.get("max_water_depth"),
                "outputs": result_meta.get("outputs", {}),
                "stats": result_meta.get("stats", {}),
                "workspace": self.builder.workspace_path,
                "output_file": result_meta.get("source_file"),
                "metadata": {
                    "source_file": result_meta.get("source_file"),
                    "variables": result_meta.get("variables"),
                    "build_metadata": self.builder.metadata if self.builder else {}
                },
                "logs": self._logs[:5000] if self._logs else ""
            }

        except Exception as e:
            self.error_message = f"Failed to parse Delft3D results: {e}"
            self.status = "FAILED"
            logger.exception("Result parsing failed")
            return {}
