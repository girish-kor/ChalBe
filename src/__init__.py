# ...existing code...
"""
Top-level package for chalbe CLI utilities.

This module exposes a tiny, lazy API to avoid heavy imports at package import time.
"""
from typing import Callable

# Try to get package version from installed metadata; fall back to a sensible default.
try:
    from importlib.metadata import version as _pkg_version, PackageNotFoundError  # type: ignore
    try:
        __version__ = _pkg_version("chalbe")
    except PackageNotFoundError:
        __version__ = "0.0.0"
except Exception:
    __version__ = "0.0.0"


def main() -> int:
    """
    Entry point for running the CLI programmatically.

    Imports the real main() lazily to avoid loading heavy dependencies on import.
    Returns the value returned by the underlying main().
    """
    from .main import main as _main  # lazy import
    return _main()


def get_cli() -> Callable:
    """
    Return the Click CLI group (for integration/tests). Imported lazily.
    """
    from .commands import cli as _cli  # lazy import
    return _cli


# Optional convenience re-exports (lazy wrappers) for some utilities used by callers/tests.
def run_cmd(cmd: str, capture: bool = False, check: bool = False):
    from .utils import run_cmd as _run_cmd  # lazy import
    return _run_cmd(cmd, capture=capture, check=check)


def shutil_which(name: str):
    from .utils import shutil_which as _which  # lazy import
    return _which(name)


__all__ = ["main", "get_cli", "run_cmd", "shutil_which", "__version__"]
