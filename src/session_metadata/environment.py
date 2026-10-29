import importlib.metadata
import platform
import subprocess
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def app_version() -> dict[str, Any]:
    """Commit hash of the running code (+ whether the tree had local changes)."""

    def git(*args: str) -> str | None:
        try:
            out = subprocess.run(
                ["git", *args],
                cwd=_REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return out.stdout.strip() if out.returncode == 0 else None

    status = git("status", "--porcelain")
    return {
        "commit": git("rev-parse", "HEAD") or "unknown",
        "dirty": None if status is None else bool(status),
    }


def sdk_version() -> str:
    try:
        return importlib.metadata.version("brainaccess")
    except importlib.metadata.PackageNotFoundError:
        return "not installed"


def system_info(refresh_rate_hz: float) -> dict[str, Any]:
    return {
        "os": platform.platform(),
        "python": platform.python_version(),
        "brainaccess_sdk": sdk_version(),
        "monitor_refresh_rate_hz": refresh_rate_hz,
    }
