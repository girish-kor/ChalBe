"""Alias `chalbe.commands` to the real implementation at `src.commands`.

This ensures tests and runtime code that import or patch
`chalbe.commands` operate on the actual module object defined in
`src.commands` (no in-memory shadowing). It also preserves entry points
that expect `chalbe.commands.cli` to exist.
"""

import importlib
import sys

# Import the real implementation
_real = importlib.import_module("src.commands")

# Replace this module in sys.modules with the real implementation so that
# `import chalbe.commands` yields the src.commands module object.
sys.modules[__name__] = _real
