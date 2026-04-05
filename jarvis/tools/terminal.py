import subprocess
import logging
import platform

logger = logging.getLogger(__name__)


class Terminal:
    """Shell command execution with timeout and encoding handling."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def run(self, command: str, timeout: int | None = None) -> dict:
        """Execute a shell command and return stdout/stderr."""
        try:
            shell = platform.system() == "Windows"
            result = subprocess.run(
                command,
                shell=shell,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout or self.timeout,
            )
            output = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "command": command,
            }
            if result.returncode != 0:
                return {
                    "success": False,
                    "output": output,
                    "error": result.stderr.strip() if result.stderr else f"Exit code {result.returncode}",
                }
            return {"success": True, "output": output, "error": None}
        except subprocess.TimeoutExpired:
            return {"success": False, "output": None, "error": f"Command timed out after {timeout or self.timeout}s"}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}
