import abc
import uuid
from typing import Dict, Any

class SimulationEngine(abc.ABC):
    """
    Abstract base class for all flood simulation engines (e.g., SPH, Delft3D).
    """

    def __init__(self, scenario_config: Dict[str, Any]):
        self.config = scenario_config
        self.simulation_id = str(uuid.uuid4())
        self.status = "PENDING"
        self.error_message = None

    @abc.abstractmethod
    def validate(self) -> bool:
        """Validates if the engine can run the given configuration."""
        pass

    @abc.abstractmethod
    def prepare(self) -> None:
        """Prepares boundaries, meshes, or initial particle states."""
        pass

    @abc.abstractmethod
    def run(self) -> None:
        """Executes the core simulation loop or subprocess."""
        pass

    @abc.abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Returns the current progress or state of the simulation."""
        pass

    @abc.abstractmethod
    def cancel(self) -> None:
        """Gracefully halts the simulation."""
        pass

    @abc.abstractmethod
    def load_results(self) -> Dict[str, Any]:
        """Parses output files or arrays into the unified results format."""
        pass
