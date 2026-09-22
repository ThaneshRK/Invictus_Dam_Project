import abc
import os
import subprocess
import time
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class Delft3DExecutor(abc.ABC):
    """Abstract executor for Delft3D D-Flow FM."""

    def __init__(self, workspace_path: str = "", mdu_filename: str = ""):
        self.workspace_path = workspace_path
        self.mdu_filename = mdu_filename
        self.mdu_path = os.path.join(workspace_path, mdu_filename) if workspace_path else ""
        self.process: Optional[subprocess.Popen] = None
        self.start_time = 0
        self.exit_code: Optional[int] = None
        self.error_message: Optional[str] = None
        self.stdout_log = os.path.join(workspace_path, "logs", "dflowfm.out") if workspace_path else ""
        self.stderr_log = os.path.join(workspace_path, "logs", "dflowfm.err") if workspace_path else ""

        # Ensure log directory exists
        if workspace_path:
            os.makedirs(os.path.join(workspace_path, "logs"), exist_ok=True)

    @abc.abstractmethod
    def build_command(self) -> list[str]:
        """Constructs the execution command."""
        pass

    def get_environment(self) -> dict:
        """Returns environment variables for the subprocess."""
        env = os.environ.copy()
        existing_ld = env.get("LD_LIBRARY_PATH", "")
        delft3d_ld = settings.DELFT3D_LD_LIBRARY_PATH
        if existing_ld:
            env["LD_LIBRARY_PATH"] = f"{delft3d_ld}:{existing_ld}"
        else:
            env["LD_LIBRARY_PATH"] = delft3d_ld
        return env

    def start(self) -> None:
        """Starts the execution asynchronously."""
        cmd = self.build_command()
        logger.info(f"Starting Delft3D: {' '.join(cmd)}")
        logger.info(f"Working directory: {self.workspace_path}")

        try:
            self.start_time = time.time()
            self._stdout_file = open(self.stdout_log, "w")
            self._stderr_file = open(self.stderr_log, "w")

            env = self.get_environment()

            self.process = subprocess.Popen(
                cmd,
                stdout=self._stdout_file,
                stderr=self._stderr_file,
                cwd=self.workspace_path,
                env=env,
                text=True
            )
            logger.info(f"Delft3D process started with PID {self.process.pid}")
        except Exception as e:
            self.exit_code = -1
            self.error_message = str(e)
            logger.error(f"Failed to start Delft3D: {e}")

    def poll(self) -> Optional[int]:
        """Checks if process is finished. Returns exit code or None if running."""
        if self.process is None:
            return self.exit_code

        code = self.process.poll()
        if code is not None:
            self.exit_code = code
            self._close_logs()

            if code != 0:
                self.error_message = f"dflowfm exited with code {code}"
                try:
                    with open(self.stderr_log, "r") as f:
                        lines = f.readlines()
                        if lines:
                            self.error_message += f": {''.join(lines[-10:]).strip()}"
                except Exception:
                    pass
                logger.error(self.error_message)
            else:
                elapsed = time.time() - self.start_time
                logger.info(f"Delft3D completed successfully in {elapsed:.1f}s")

        return self.exit_code

    def wait(self, timeout: Optional[int] = None) -> int:
        """Blocks until the process finishes or timeout is reached."""
        if self.process is None:
            return self.exit_code or -1

        effective_timeout = timeout or settings.DELFT3D_TIMEOUT_SECONDS
        try:
            self.process.wait(timeout=effective_timeout)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.exit_code = -2
            self.error_message = f"Delft3D timed out after {effective_timeout}s"
            self._close_logs()
            return self.exit_code

        return self.poll()

    def cancel(self) -> None:
        """Terminates the running process."""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.exit_code = -9
            self.error_message = "Cancelled by user"
            self._close_logs()

    def _close_logs(self):
        if hasattr(self, '_stdout_file') and not self._stdout_file.closed:
            self._stdout_file.close()
        if hasattr(self, '_stderr_file') and not self._stderr_file.closed:
            self._stderr_file.close()

    def get_logs(self) -> str:
        """Read captured logs."""
        logs = []
        for path in [self.stdout_log, self.stderr_log]:
            try:
                with open(path, "r") as f:
                    content = f.read()
                    if content.strip():
                        logs.append(content)
            except Exception:
                pass
        return "\n".join(logs)


class HostDelft3DExecutor(Delft3DExecutor):
    """Executes Delft3D directly on the host using the installed run_dflowfm.sh."""

    def validate_installation(self) -> bool:
        run_script = os.path.join(settings.DELFT3D_INSTALL_DIR, "bin", "run_dflowfm.sh")
        return os.path.exists(run_script)

    def build_command(self) -> list[str]:
        run_script = os.path.join(settings.DELFT3D_INSTALL_DIR, "bin", "run_dflowfm.sh")
        if not os.path.exists(run_script):
            raise FileNotFoundError(f"run_dflowfm.sh not found at {run_script}")
        return ["bash", run_script, self.mdu_filename]


class DockerDelft3DExecutor(Delft3DExecutor):
    """Executes Delft3D inside a Docker container mapped to the workspace."""

    def validate_installation(self) -> bool:
        res = subprocess.run(["docker", "image", "inspect", settings.DELFT3D_CONTAINER_IMAGE], capture_output=True)
        return res.returncode == 0

    def build_command(self) -> list[str]:
        image = settings.DELFT3D_CONTAINER_IMAGE
        return [
            "docker", "run", "--rm",
            "-v", f"{self.workspace_path}:/workspace",
            "-w", "/workspace",
            image,
            "dflowfm", "--nodisplay", "--autostartstop", self.mdu_filename
        ]


