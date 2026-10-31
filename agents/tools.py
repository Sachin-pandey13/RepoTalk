import os

from backend.services.scanner_service import scan_repository
from backend.services.parser_service import parse_repository
from backend.services.embedding_service import semantic_search


def _resolve_repo_path(repo_name: str) -> str:
    """
    Resolve a repository name to a local repository path.

    Supported forms:
    - "."
    - an existing absolute/relative path
    - a repository inside workspace/
    """

    if not repo_name:
        return "."

    # Direct path
    if os.path.exists(repo_name):
        return os.path.abspath(repo_name)

    # Repository inside workspace/
    workspace_path = os.path.join(
        "workspace",
        repo_name
    )

    if os.path.exists(workspace_path):
        return os.path.abspath(workspace_path)

    return os.path.abspath(repo_name)


def _is_path_inside(
    parent_path: str,
    target_path: str
) -> bool:
    """
    Safely determine whether target_path is inside parent_path.
    """

    parent_path = os.path.abspath(parent_path)
    target_path = os.path.abspath(target_path)

    try:
        return os.path.commonpath(
            [parent_path, target_path]
        ) == parent_path

    except ValueError:
        # Different drives on Windows, for example.
        return False


def _is_safe_repo_file(
    repo_name: str,
    file_path: str
) -> bool:
    """
    Ensure the requested file belongs to the selected repository.
    """

    repo_path = _resolve_repo_path(repo_name)

    if not os.path.exists(repo_path):
        return False

    # Convert relative file paths relative to current working directory.
    target_path = os.path.abspath(file_path)

    return _is_path_inside(
        repo_path,
        target_path
    )


def list_repository(repo_name: str) -> dict:
    """
    Lists repository structure, total files,
    and language breakdown.
    """

    repo_path = _resolve_repo_path(repo_name)

    if not os.path.exists(repo_path):
        return {
            "error": (
                f"Repository path '{repo_path}' "
                "does not exist."
            )
        }

    return scan_repository(repo_path)


def search_code(
    repo_name: str,
    query: str,
    top_k: int = 5
) -> list:
    """
    Performs semantic vector search only within
    the selected repository.
    """

    if not query:
        return [{
            "error": "Search query cannot be empty."
        }]

    try:

        results = semantic_search(
            query,
            repo_name,
            top_k=top_k
        )

        return results

    except Exception as e:

        return [{
            "error": (
                f"Semantic search failed: {str(e)}"
            )
        }]


def read_file(
    repo_name: str,
    file_path: str,
    start_line: int = 1,
    max_lines: int = 100
) -> dict:
    """
    Reads a section of a file.

    Access is restricted to files inside
    the selected repository.
    """

    if not file_path:
        return {
            "error": "file_path is required."
        }

    repo_path = _resolve_repo_path(repo_name)

    if not os.path.exists(repo_path):
        return {
            "error": (
                f"Repository '{repo_name}' "
                "does not exist."
            )
        }

    # Resolve paths that may be returned as either:
    # backend/routes/repo.py
    # ./backend/routes/repo.py
    # D:/RepoTalk/backend/routes/repo.py
    target_path = os.path.abspath(
        file_path
    )

    # If the supplied path does not exist directly,
    # try resolving it relative to the repository.
    if not os.path.exists(target_path):

        repo_relative_path = os.path.abspath(
            os.path.join(
                repo_path,
                file_path
            )
        )

        if os.path.exists(repo_relative_path):
            target_path = repo_relative_path

    # Security boundary.
    if not _is_path_inside(
        repo_path,
        target_path
    ):
        return {
            "error": (
                "Access denied: requested file "
                "is outside the selected repository."
            )
        }

    if not os.path.isfile(target_path):
        return {
            "error": (
                f"File '{file_path}' "
                "was not found."
            )
        }

    try:

        with open(
            target_path,
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as f:

            lines = f.readlines()

        total_lines = len(lines)

        start_line = max(
            int(start_line),
            1
        )

        max_lines = max(
            int(max_lines),
            1
        )

        start_idx = start_line - 1

        end_idx = min(
            total_lines,
            start_idx + max_lines
        )

        selected_lines = [
            f"{i + 1}: {lines[i]}"
            for i in range(
                start_idx,
                end_idx
            )
        ]

        return {
            "file_path": target_path,
            "total_lines": total_lines,
            "showing_start": (
                start_idx + 1
            ),
            "showing_end": end_idx,
            "content": "".join(
                selected_lines
            )
        }

    except Exception as e:

        return {
            "error": (
                f"Failed to read file "
                f"'{file_path}': {str(e)}"
            )
        }


def inspect_symbol(
    repo_name: str,
    symbol_name: str
) -> dict:
    """
    Searches AST parsed data for a specific
    function or class definition.
    """

    if not symbol_name:
        return {
            "error": (
                "symbol_name is required."
            )
        }

    repo_path = _resolve_repo_path(
        repo_name
    )

    if not os.path.exists(repo_path):
        return {
            "error": (
                f"Repository path '{repo_path}' "
                "does not exist."
            )
        }

    parsed = parse_repository(
        repo_path
    )

    found_definitions = []

    for file_data in parsed.get(
        "parsed_files",
        []
    ):

        file_path = file_data.get(
            "file",
            ""
        )

        if symbol_name in file_data.get(
            "functions",
            []
        ):

            found_definitions.append({
                "type": "function",
                "symbol": symbol_name,
                "file": file_path
            })

        if symbol_name in file_data.get(
            "classes",
            []
        ):

            found_definitions.append({
                "type": "class",
                "symbol": symbol_name,
                "file": file_path
            })

    return {
        "symbol": symbol_name,
        "matches_found": len(
            found_definitions
        ),
        "definitions": found_definitions
    }


def find_callers(
    repo_name: str,
    function_name: str
) -> dict:
    """
    Finds functions in the selected repository
    that invoke the specified function.
    """

    if not function_name:
        return {
            "error": (
                "function_name is required."
            )
        }

    repo_path = _resolve_repo_path(
        repo_name
    )

    if not os.path.exists(repo_path):
        return {
            "error": (
                f"Repository path '{repo_path}' "
                "does not exist."
            )
        }

    parsed = parse_repository(
        repo_path
    )

    callers = []

    for file_data in parsed.get(
        "parsed_files",
        []
    ):

        file_path = file_data.get(
            "file",
            ""
        )

        for call_info in file_data.get(
            "function_calls",
            []
        ):

            caller_func = call_info.get(
                "function"
            )

            called_funcs = call_info.get(
                "calls",
                []
            )

            if function_name in called_funcs:

                callers.append({
                    "caller_function": caller_func,
                    "file": file_path
                })

    return {
        "target_function": function_name,
        "caller_count": len(callers),
        "callers": callers
    }


def find_callees(
    repo_name: str,
    function_name: str
) -> dict:
    """
    Finds all functions called by the
    specified function.
    """

    if not function_name:
        return {
            "error": (
                "function_name is required."
            )
        }

    repo_path = _resolve_repo_path(
        repo_name
    )

    if not os.path.exists(repo_path):
        return {
            "error": (
                f"Repository path '{repo_path}' "
                "does not exist."
            )
        }

    parsed = parse_repository(
        repo_path
    )

    callees = []

    for file_data in parsed.get(
        "parsed_files",
        []
    ):

        file_path = file_data.get(
            "file",
            ""
        )

        for call_info in file_data.get(
            "function_calls",
            []
        ):

            caller_func = call_info.get(
                "function"
            )

            if caller_func == function_name:

                for called in call_info.get(
                    "calls",
                    []
                ):

                    callees.append({
                        "callee_function": called,
                        "file": file_path
                    })

    return {
        "target_function": function_name,
        "callee_count": len(callees),
        "callees": callees
    }


def find_dependencies(
    repo_name: str,
    file_path: str = None
) -> dict:
    """
    Retrieves file import dependencies across
    the selected repository or for a specific file.
    """

    repo_path = _resolve_repo_path(
        repo_name
    )

    if not os.path.exists(repo_path):
        return {
            "error": (
                f"Repository path '{repo_path}' "
                "does not exist."
            )
        }

    parsed = parse_repository(
        repo_path
    )

    dep_graph = parsed.get(
        "dependency_graph",
        []
    )

    if file_path:

        # Resolve the supplied path so comparisons
        # work with both relative and absolute paths.
        requested_path = os.path.abspath(
            file_path
        )

        if not os.path.exists(
            requested_path
        ):

            requested_path = os.path.abspath(
                os.path.join(
                    repo_path,
                    file_path
                )
            )

        # Do not allow dependency inspection
        # outside the selected repository.
        if not _is_path_inside(
            repo_path,
            requested_path
        ):
            return {
                "error": (
                    "Access denied: requested file "
                    "is outside the selected repository."
                )
            }

        requested_basename = os.path.basename(
            requested_path
        )

        for node in dep_graph:

            node_file = node.get(
                "file",
                ""
            )

            node_path = os.path.abspath(
                node_file
            )

            if (
                node_path == requested_path
                or os.path.basename(
                    node_path
                ) == requested_basename
            ):

                return {
                    "file": node_file,
                    "dependencies": node.get(
                        "dependencies",
                        []
                    )
                }

        return {
            "error": (
                f"File '{file_path}' "
                "not found in dependency graph."
            )
        }

    return {
        "repository": repo_path,
        "dependency_graph": dep_graph
    }