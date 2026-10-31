"""
backend/services/parser_service.py

Multi-language repository parser.

• Python  – full AST via tree-sitter-python (functions, classes, imports,
            call graph, docstrings, line numbers)
• JS/TS   – lightweight regex extraction (functions, classes, imports)
• Other   – raw source is still chunked and indexed so semantic search works

The module also caches parse results per (repo_path, mtime) so re-scans
triggered by the agent loop don't re-parse unchanged files.
"""
from __future__ import annotations

import ast
import os
import re
import hashlib
from typing import Any

# ── optional tree-sitter ──────────────────────────────────────────────────────
try:
    from tree_sitter import Language, Parser as TSParser
    import tree_sitter_python as tspython
    _PY_LANGUAGE = Language(tspython.language())
    _ts_parser = TSParser(_PY_LANGUAGE)
    USE_TREE_SITTER = True
except Exception:
    USE_TREE_SITTER = False

from backend.services.graph_service import build_dependency_graph

# ── parse cache (repo_path → result) ─────────────────────────────────────────
_parse_cache: dict[str, dict] = {}

IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", "venv", ".venv",
    "dist", "build", ".next", ".mypy_cache", ".pytest_cache",
}

SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".java", ".go", ".rs", ".cpp", ".c", ".cs",
    ".rb", ".php", ".swift", ".kt",
}

# ── helpers ───────────────────────────────────────────────────────────────────

def _repo_fingerprint(repo_path: str) -> str:
    """Return a hash of the most recent mtime of any source file."""
    h = hashlib.md5()
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = sorted(d for d in dirs if d not in IGNORE_DIRS)
        for f in sorted(files):
            ext = os.path.splitext(f)[1]
            if ext in SOURCE_EXTENSIONS:
                try:
                    mtime = os.path.getmtime(os.path.join(root, f))
                    h.update(f"{f}{mtime}".encode())
                except OSError:
                    pass
    return h.hexdigest()


# ── Python parser (tree-sitter preferred, ast fallback) ──────────────────────

def _parse_python_ts(source: str, file_path: str) -> dict:
    """Parse Python with tree-sitter for full AST detail."""
    tree = _ts_parser.parse(bytes(source, "utf8"))
    root = tree.root_node

    functions: list[dict] = []
    classes: list[str] = []
    imports: list[str] = []
    function_calls: list[dict] = []

    def _get_docstring(node) -> str | None:
        body = node.child_by_field_name("body")
        if body and body.children:
            first = body.children[0]
            if first.type == "expression_statement":
                expr = first.children[0] if first.children else None
                if expr and expr.type == "string":
                    return expr.text.decode("utf-8", errors="ignore").strip('"\' \n')
        return None

    def _collect_calls(node, out: list) -> None:
        if node.type == "call":
            fn = node.child_by_field_name("function")
            if fn:
                out.append(fn.text.decode("utf-8", errors="ignore"))
        for child in node.children:
            _collect_calls(child, out)

    def _walk(node, class_name: str | None = None) -> None:
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                fname = name_node.text.decode("utf-8", errors="ignore")
                calls: list[str] = []
                _collect_calls(node, calls)
                functions.append({
                    "name": fname,
                    "line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "class": class_name,
                    "docstring": _get_docstring(node),
                })
                function_calls.append({"function": fname, "calls": calls})
            # recurse into nested functions
            for child in node.children:
                _walk(child, class_name)

        elif node.type == "class_definition":
            cname_node = node.child_by_field_name("name")
            cname = cname_node.text.decode("utf-8", errors="ignore") if cname_node else ""
            classes.append(cname)
            for child in node.children:
                _walk(child, class_name=cname)

        elif node.type in ("import_statement", "import_from_statement"):
            imports.append(node.text.decode("utf-8", errors="ignore"))
        else:
            for child in node.children:
                _walk(child, class_name)

    _walk(root)
    return {
        "functions": functions,
        "classes": classes,
        "imports": imports,
        "function_calls": function_calls,
        "source": source,
    }


def _parse_python_ast(source: str, file_path: str) -> dict:
    """Fallback Python parser using stdlib ast."""
    tree = ast.parse(source)
    functions: list[dict] = []
    classes: list[str] = []
    imports: list[str] = []
    function_calls: list[dict] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            calls = [
                (n.func.id if isinstance(n.func, ast.Name) else
                 n.func.attr if isinstance(n.func, ast.Attribute) else "")
                for n in ast.walk(node) if isinstance(n, ast.Call)
            ]
            doc = ast.get_docstring(node)
            functions.append({
                "name": node.name,
                "line": node.lineno,
                "end_line": node.end_lineno or node.lineno,
                "class": None,
                "docstring": doc,
            })
            function_calls.append({"function": node.name, "calls": [c for c in calls if c]})
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            names = ", ".join(a.name for a in node.names)
            imports.append(f"from {mod} import {names}")

    return {
        "functions": functions,
        "classes": classes,
        "imports": imports,
        "function_calls": function_calls,
        "source": source,
    }


def _parse_python(source: str, file_path: str) -> dict:
    if USE_TREE_SITTER:
        try:
            return _parse_python_ts(source, file_path)
        except Exception:
            pass
    try:
        return _parse_python_ast(source, file_path)
    except SyntaxError:
        pass
    return {"functions": [], "classes": [], "imports": [], "function_calls": [], "source": source}


# ── JS / TS parser (regex) ────────────────────────────────────────────────────

_JS_FUNC_RE = re.compile(
    r"(?:export\s+)?(?:async\s+)?function\s+(\w+)"
    r"|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(",
    re.MULTILINE,
)
_JS_CLASS_RE = re.compile(r"class\s+(\w+)", re.MULTILINE)
_JS_IMPORT_RE = re.compile(
    r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]"
    r"|require\(['\"]([^'\"]+)['\"]\)",
    re.MULTILINE,
)
_JS_ARROW_NAMED = re.compile(
    r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(.*?\)\s*=>",
    re.MULTILINE,
)


def _parse_js(source: str) -> dict:
    functions: list[dict] = []
    classes: list[str] = []
    imports: list[str] = []

    for m in _JS_FUNC_RE.finditer(source):
        name = m.group(1) or m.group(2)
        if name:
            lineno = source[: m.start()].count("\n") + 1
            functions.append({"name": name, "line": lineno, "end_line": lineno, "class": None, "docstring": None})

    for m in _JS_ARROW_NAMED.finditer(source):
        name = m.group(1)
        if name and not any(f["name"] == name for f in functions):
            lineno = source[: m.start()].count("\n") + 1
            functions.append({"name": name, "line": lineno, "end_line": lineno, "class": None, "docstring": None})

    for m in _JS_CLASS_RE.finditer(source):
        classes.append(m.group(1))

    for m in _JS_IMPORT_RE.finditer(source):
        imp = m.group(1) or m.group(2)
        if imp:
            imports.append(imp)

    return {
        "functions": functions,
        "classes": classes,
        "imports": imports,
        "function_calls": [],
        "source": source,
    }


# ── Generic / other languages ─────────────────────────────────────────────────

def _parse_generic(source: str) -> dict:
    """Return minimal metadata so source is still chunked and indexed."""
    return {
        "functions": [],
        "classes": [],
        "imports": [],
        "function_calls": [],
        "source": source,
    }


# ── Per-file dispatcher ───────────────────────────────────────────────────────

def parse_file(file_path: str) -> dict:
    """Parse a single source file and return its metadata + raw source."""
    ext = os.path.splitext(file_path)[1].lower()
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
    except OSError as exc:
        return {"file": file_path, "error": str(exc)}

    if ext == ".py":
        data = _parse_python(source, file_path)
    elif ext in (".js", ".jsx", ".ts", ".tsx"):
        data = _parse_js(source)
    else:
        data = _parse_generic(source)

    data["file"] = file_path
    # Flatten function names for backward-compat callers
    data["function_names"] = [
        f["name"] if isinstance(f, dict) else f for f in data["functions"]
    ]
    return data


# ── Repository-level parser ───────────────────────────────────────────────────

def parse_repository(repo_path: str, force: bool = False) -> dict:
    """
    Walk *repo_path*, parse every source file, build the dependency graph.

    Results are cached by (repo_path, fingerprint) so repeated calls inside
    the agent loop are cheap.
    """
    repo_path = os.path.abspath(repo_path)
    fingerprint = _repo_fingerprint(repo_path)
    cache_key = f"{repo_path}::{fingerprint}"

    if not force and cache_key in _parse_cache:
        return _parse_cache[cache_key]

    parsed_files: list[dict] = []

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = sorted(d for d in dirs if d not in IGNORE_DIRS)
        for fname in sorted(files):
            ext = os.path.splitext(fname)[1].lower()
            if ext not in SOURCE_EXTENSIONS:
                continue
            fpath = os.path.join(root, fname)
            result = parse_file(fpath)
            parsed_files.append(result)

    dependency_graph = build_dependency_graph(parsed_files)

    output = {
        "repository": repo_path,
        "parsed_files": parsed_files,
        "dependency_graph": dependency_graph,
    }
    _parse_cache[cache_key] = output
    return output