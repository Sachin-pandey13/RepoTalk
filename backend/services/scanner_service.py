import os
from collections import Counter

IGNORE_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    "venv"
}

LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".java": "Java",
    ".cpp": "C++",
    ".c": "C",
    ".go": "Go",
    ".rs": "Rust",
    ".html": "HTML",
    ".css": "CSS",
    ".md": "Markdown",
    ".json": "JSON",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".sh": "Shell"
}


def scan_repository(repo_path: str):

    total_files = 0
    total_dirs = 0

    extensions = []
    languages = []

    for root, dirs, files in os.walk(repo_path):

        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        total_dirs += len(dirs)

        for file in files:

            total_files += 1

            ext = os.path.splitext(file)[1]

            if ext:
                extensions.append(ext)

                if ext in LANGUAGE_MAP:
                    languages.append(LANGUAGE_MAP[ext])

    extension_count = Counter(extensions)
    language_count = Counter(languages)

    return {
        "total_files": total_files,
        "total_directories": total_dirs,
        "extensions": dict(extension_count),
        "languages": dict(language_count)
    }