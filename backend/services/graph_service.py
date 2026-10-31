"""
backend/services/graph_service.py

Builds an import dependency graph from parsed file data.

Improvements over the original:
 - Handles `from __future__ import`, `from . import` (relative imports)
 - Normalises module names (strips leading dots)
 - Deduplicates dependencies per file
 - Returns both raw module names and resolved peer files where possible
"""
from __future__ import annotations

import os
import re

_REL_DOTS = re.compile(r"^\.+")


def _normalise_module(module: str) -> str:
    """Strip leading relative-import dots and return the base module name."""
    return _REL_DOTS.sub("", module).strip()


def _extract_module(imp_str: str) -> str | None:
    """
    Extract the top-level module name from an import string such as:
        from backend.services.foo import bar  → backend
        import os.path                        → os
        from . import utils                   → (empty, skip)
    """
    imp_str = imp_str.strip()

    if imp_str.startswith("from "):
        parts = imp_str.split()
        if len(parts) >= 2:
            mod = _normalise_module(parts[1])
            return mod.split(".")[0] if mod else None

    elif imp_str.startswith("import "):
        parts = imp_str.split()
        if len(parts) >= 2:
            # handle `import os, sys`
            mods = [p.strip(",") for p in parts[1:]]
            return mods[0].split(".")[0] if mods else None

    return None


def build_dependency_graph(parsed_files: list[dict]) -> list[dict]:
    """
    Return a list of {file, dependencies} dicts where *dependencies* is a
    deduplicated list of top-level module names imported by that file.

    The graph can be used by the agent's find_dependencies tool to understand
    the import structure of a repository without reading every file.
    """
    # Build an index of all known file basenames so we can tag internal deps
    known_basenames: set[str] = set()
    for fd in parsed_files:
        fp = fd.get("file", "")
        if fp:
            known_basenames.add(os.path.splitext(os.path.basename(fp))[0])

    graph: list[dict] = []

    for file_data in parsed_files:
        current_file = file_data.get("file", "")
        raw_imports: list[str] = file_data.get("imports", [])

        deps: list[str] = []
        seen: set[str] = set()

        for imp in raw_imports:
            mod = _extract_module(str(imp))
            if mod and mod not in seen and mod != "__future__":
                seen.add(mod)
                deps.append(mod)

        graph.append({
            "file": current_file,
            "dependencies": deps,
            # Tag whether each dep is an internal project module
            "internal": [d for d in deps if d in known_basenames],
            "external": [d for d in deps if d not in known_basenames],
        })

    return graph