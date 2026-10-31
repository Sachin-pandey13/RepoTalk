"""
agents/tools.py

Tool implementations called by RepositoryAgent._execute_tool().

Each tool is scoped to a single repository — path traversal outside that
repository is explicitly blocked at the _is_safe_repo_file boundary.
"""
from __future__ import annotations

import os
from typing import Any

from backend.services.scanner_service import scan_repository
from backend.services.parser_service import parse_repository
from backend.services.embedding_service import semantic_search


# ── Path utilities ────────────────────────────────────────────────────────────

def _resolve_repo_path(repo_name: str) -> str:
    """
    Resolve a repository name to its absolute local path.

    Priority:
    1. Direct absolute/relative path that exists
    2. workspace/<repo_name>
    3. Absolute path of repo_name (even if it doesn't exist — caller checks)
    """
    if not repo_name:
        return os.path.abspath(".")

    if os.path.exists(repo_name):
        return os.path.abspath(repo_name)

    workspace_path = os.path.join("workspace", repo_name)
    if os.path.exists(workspace_path):
        return os.path.abspath(workspace_path)

    return os.path.abspath(repo_name)


def _is_path_inside(parent_path: str, target_path: str) -> bool:
    """Return True iff *target_path* is inside *parent_path*."""
    parent = os.path.abspath(parent_path)
    target = os.path.abspath(target_path)
    try:
        return os.path.commonpath([parent, target]) == parent
    except ValueError:
        # Different drives on Windows
        return False


def _resolve_file_path(repo_path: str, file_path: str) -> str | None:
    """
    Try multiple strategies to locate *file_path* inside *repo_path*.

    Returns the resolved absolute path, or None if not found.
    """
    # 1. Absolute path as-is
    abs_path = os.path.abspath(file_path)
    if os.path.isfile(abs_path) and _is_path_inside(repo_path, abs_path):
        return abs_path

    # 2. Relative to CWD
    cwd_path = os.path.abspath(os.path.join(os.getcwd(), file_path))
    if os.path.isfile(cwd_path) and _is_path_inside(repo_path, cwd_path):
        return cwd_path

    # 3. Relative to repo root
    repo_rel = os.path.abspath(os.path.join(repo_path, file_path))
    if os.path.isfile(repo_rel) and _is_path_inside(repo_path, repo_rel):
        return repo_rel

    # 4. Basename match — walk the repo looking for the filename
    basename = os.path.basename(file_path)
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", "venv", ".venv"}]
        if basename in files:
            candidate = os.path.join(root, basename)
            if _is_path_inside(repo_path, candidate):
                return candidate

    return None


# ── Helper: flatten function list ────────────────────────────────────────────

def _fn_names(functions: list) -> list[str]:
    """Accept both old str-list and new dict-list formats."""
    out: list[str] = []
    for f in functions:
        if isinstance(f, dict):
            out.append(f.get("name", ""))
        elif isinstance(f, str):
            out.append(f)
    return [n for n in out if n]


# ── Tools ─────────────────────────────────────────────────────────────────────

def list_repository(repo_name: str) -> dict:
    """Return structure overview + file tree of the repository."""
    repo_path = _resolve_repo_path(repo_name)
    if not os.path.isdir(repo_path):
        return {"error": f"Repository path '{repo_path}' does not exist."}
    return scan_repository(repo_path)


def search_code(repo_name: str, query: str, top_k: int = 6) -> list[dict]:
    """Semantic vector search restricted to *repo_name*."""
    if not query:
        return [{"error": "Search query cannot be empty."}]
    try:
        return semantic_search(query, repo_name, top_k=top_k)
    except Exception as exc:
        return [{"error": f"Semantic search failed: {exc}"}]


def read_file(
    repo_name: str,
    file_path: str,
    start_line: int = 1,
    max_lines: int = 120,
) -> dict:
    """
    Read *max_lines* lines from *file_path* starting at *start_line*.

    Access is restricted to files inside the repository.
    """
    if not file_path:
        return {"error": "file_path is required."}

    repo_path = _resolve_repo_path(repo_name)
    if not os.path.isdir(repo_path):
        return {"error": f"Repository '{repo_name}' does not exist locally."}

    resolved = _resolve_file_path(repo_path, file_path)
    if resolved is None:
        return {"error": f"File '{file_path}' was not found inside repository '{repo_name}'."}

    if not _is_path_inside(repo_path, resolved):
        return {"error": "Access denied: file is outside the selected repository."}

    try:
        with open(resolved, "r", encoding="utf-8", errors="ignore") as fh:
            all_lines = fh.readlines()
    except OSError as exc:
        return {"error": f"Could not read '{file_path}': {exc}"}

    total_lines = len(all_lines)
    start_line = max(1, int(start_line))
    max_lines = max(1, min(int(max_lines), 300))

    start_idx = start_line - 1
    end_idx = min(total_lines, start_idx + max_lines)

    snippet = "".join(
        f"{i + 1}: {all_lines[i]}" for i in range(start_idx, end_idx)
    )

    return {
        "file_path": resolved,
        "relative_path": os.path.relpath(resolved, repo_path),
        "total_lines": total_lines,
        "showing_start": start_idx + 1,
        "showing_end": end_idx,
        "content": snippet,
    }


def inspect_symbol(repo_name: str, symbol_name: str) -> dict:
    """
    Find function/class definitions in the repository matching *symbol_name*.

    Returns exact line numbers when available (Python + tree-sitter parsed).
    """
    if not symbol_name:
        return {"error": "symbol_name is required."}

    repo_path = _resolve_repo_path(repo_name)
    if not os.path.isdir(repo_path):
        return {"error": f"Repository path '{repo_path}' does not exist."}

    parsed = parse_repository(repo_path)
    definitions: list[dict] = []

    for file_data in parsed.get("parsed_files", []):
        if "error" in file_data:
            continue

        file_path = file_data.get("file", "")

        # Functions
        for fn in file_data.get("functions", []):
            if isinstance(fn, dict):
                name = fn.get("name", "")
                if name == symbol_name or symbol_name.lower() in name.lower():
                    definitions.append({
                        "type": "function",
                        "symbol": name,
                        "file": file_path,
                        "line": fn.get("line"),
                        "end_line": fn.get("end_line"),
                        "class": fn.get("class"),
                        "docstring": fn.get("docstring"),
                    })
            elif isinstance(fn, str) and (fn == symbol_name or symbol_name.lower() in fn.lower()):
                definitions.append({
                    "type": "function",
                    "symbol": fn,
                    "file": file_path,
                    "line": None,
                    "end_line": None,
                })

        # Classes
        for cls in file_data.get("classes", []):
            cls_name = cls if isinstance(cls, str) else cls.get("name", "")
            if cls_name == symbol_name or symbol_name.lower() in cls_name.lower():
                definitions.append({
                    "type": "class",
                    "symbol": cls_name,
                    "file": file_path,
                    "line": None,
                    "end_line": None,
                })

    return {
        "symbol": symbol_name,
        "matches_found": len(definitions),
        "definitions": definitions,
    }


def find_callers(repo_name: str, function_name: str) -> dict:
    """Find all functions that call *function_name* in the repository."""
    if not function_name:
        return {"error": "function_name is required."}

    repo_path = _resolve_repo_path(repo_name)
    if not os.path.isdir(repo_path):
        return {"error": f"Repository path '{repo_path}' does not exist."}

    parsed = parse_repository(repo_path)
    callers: list[dict] = []

    for file_data in parsed.get("parsed_files", []):
        if "error" in file_data:
            continue
        file_path = file_data.get("file", "")

        for call_info in file_data.get("function_calls", []):
            caller_func = call_info.get("function", "")
            called = call_info.get("calls", [])

            # Match exact or partial (handles method.call patterns)
            if any(
                function_name == c or function_name in c
                for c in called
            ):
                callers.append({
                    "caller_function": caller_func,
                    "file": file_path,
                })

    return {
        "target_function": function_name,
        "caller_count": len(callers),
        "callers": callers,
    }


def find_callees(repo_name: str, function_name: str) -> dict:
    """Find all functions called by *function_name*."""
    if not function_name:
        return {"error": "function_name is required."}

    repo_path = _resolve_repo_path(repo_name)
    if not os.path.isdir(repo_path):
        return {"error": f"Repository path '{repo_path}' does not exist."}

    parsed = parse_repository(repo_path)
    callees: list[dict] = []

    for file_data in parsed.get("parsed_files", []):
        if "error" in file_data:
            continue
        file_path = file_data.get("file", "")

        for call_info in file_data.get("function_calls", []):
            if call_info.get("function") == function_name:
                for called in call_info.get("calls", []):
                    callees.append({
                        "callee_function": called,
                        "file": file_path,
                    })

    return {
        "target_function": function_name,
        "callee_count": len(callees),
        "callees": callees,
    }


def find_dependencies(repo_name: str, file_path: str | None = None) -> dict:
    """
    Return import dependencies for *file_path*, or the full dependency graph
    if *file_path* is None.
    """
    repo_path = _resolve_repo_path(repo_name)
    if not os.path.isdir(repo_path):
        return {"error": f"Repository path '{repo_path}' does not exist."}

    parsed = parse_repository(repo_path)
    dep_graph: list[dict] = parsed.get("dependency_graph", [])

    if not file_path:
        return {
            "repository": repo_path,
            "dependency_graph": dep_graph,
        }

    # Security check
    resolved = _resolve_file_path(repo_path, file_path)
    if resolved and not _is_path_inside(repo_path, resolved):
        return {"error": "Access denied: file is outside the selected repository."}

    target_basename = os.path.basename(file_path)

    for node in dep_graph:
        node_file = node.get("file", "")
        node_abs = os.path.abspath(node_file)
        node_rel = os.path.relpath(node_abs, repo_path)

        if (
            os.path.basename(node_file) == target_basename
            or (resolved and node_abs == resolved)
            or node_rel == file_path
        ):
            return {
                "file": node_file,
                "dependencies": node.get("dependencies", []),
                "internal": node.get("internal", []),
                "external": node.get("external", []),
            }

    return {"error": f"File '{file_path}' not found in dependency graph."}