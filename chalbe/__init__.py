"""Lightweight shim package for tests and in-repo usage.

This package re-exports modules from the in-tree `src` package so tests
that import `chalbe.*` will resolve when the project isn't installed.
"""

from importlib import import_module
from types import ModuleType
import sys


def _lazy_import(name: str) -> ModuleType:
    # Import the corresponding module from the 'src' package if available.
    try:
        mod = import_module(f"src.{name}")
        return mod
    except Exception:
        # Fall back to importing `name` directly to preserve normal behavior
        return import_module(name)


def __getattr__(name: str):
    # Provide attribute access like `from chalbe import commands` by lazily
    # importing the equivalent module from `src`.
    if name == "commands":
        return _lazy_import("commands")
    if name == "ai_prompts":
        return _lazy_import("ai_prompts")
    if name == "utils":
        return _lazy_import("utils")
    if name == "config":
        return _lazy_import("config")
    # Default: try to import a similarly named module from src
    return _lazy_import(name)


__all__ = ["commands", "ai_prompts", "utils", "config"]
