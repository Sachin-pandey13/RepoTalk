"""
backend/services/scanner_service.py

Scans a repository directory and returns:
 - total file / directory counts
 - language breakdown
 - a compact file-tree string (used by list_repository tool)
"""
from __future__ import annotations

import os
from collections import Counter

IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", "venv", ".venv",
    "dist", "build", ".next", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", "coverage", ".tox",
}

LANGUAGE_MAP = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript (JSX)",
    ".ts": "TypeScript", ".tsx": "TypeScript (TSX)",
    ".java": "Java", ".kt": "Kotlin", ".scala": "Scala",
    ".go": "Go", ".rs": "Rust",
    ".cpp": "C++", ".cc": "C++", ".cxx": "C++",
    ".c": "C", ".h": "C/C++ Header",
    ".cs": "C#", ".rb": "Ruby", ".php": "PHP",
    ".swift": "Swift", ".m": "Objective-C",
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell",
    ".html": "HTML", ".htm": "HTML",
    ".css": "CSS", ".scss": "SCSS", ".sass": "SCSS",
    ".md": "Markdown", ".mdx": "MDX",
    ".json": "JSON", ".json5": "JSON",
    ".yml": "YAML", ".yaml": "YAML",
    ".toml": "TOML", ".ini": "INI", ".cfg": "INI",
    ".env": "Env", ".sql": "SQL",
    ".graphql": "GraphQL", ".proto": "Protobuf",
    ".dockerfile": "Dockerfile",
}

_MAX_TREE_DEPTH = 4
_MAX_TREE_FILES = 300


def _build_tree(root_path: str) -> str:
    """Return an indented file tree string (depth-limited)."""
    lines: list[str] = []
    root_name = os.path.basename(root_path)
    lines.append(f"{root_name}/")

    def _walk(path: str, prefix: str, depth: int) -> None:
        if depth > _MAX_TREE_DEPTH or len(lines) > _MAX_TREE_FILES:
            return
        try:
            entries = sorted(os.scandir(path), key=lambda e: (e.is_file(), e.name.lower()))
        except PermissionError:
            return

        visible = [e for e in entries if e.name not in IGNORE_DIRS]
        for i, entry in enumerate(visible):
            if len(lines) > _MAX_TREE_FILES:
                lines.append(f"{prefix}└── … (truncated)")
                return
            connector = "└── " if i == len(visible) - 1 else "├── "
            if entry.is_dir():
                lines.append(f"{prefix}{connector}{entry.name}/")
                extension = "    " if i == len(visible) - 1 else "│   "
                _walk(entry.path, prefix + extension, depth + 1)
            else:
                lines.append(f"{prefix}{connector}{entry.name}")

    _walk(root_path, "", 1)
    return "\n".join(lines)


def scan_repository(repo_path: str) -> dict:
    """
    Return a rich overview of *repo_path* including:
      - total_files, total_directories
      - languages (counted)
      - extensions (counted)
      - file_tree (indented string)
    """
    total_files = 0
    total_dirs = 0
    extensions: list[str] = []
    languages: list[str] = []

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        total_dirs += len(dirs)

        for fname in files:
            total_files += 1
            ext = os.path.splitext(fname)[1].lower()
            if ext:
                extensions.append(ext)
                lang = LANGUAGE_MAP.get(ext)
                if lang:
                    languages.append(lang)

    ext_count = dict(Counter(extensions).most_common(20))
    lang_count = dict(Counter(languages).most_common(15))
    tree = _build_tree(repo_path)

    return {
        "repository": repo_path,
        "total_files": total_files,
        "total_directories": total_dirs,
        "extensions": ext_count,
        "languages": lang_count,
        "file_tree": tree,
    }