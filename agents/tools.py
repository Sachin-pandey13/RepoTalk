import os
from backend.services.scanner_service import scan_repository
from backend.services.parser_service import parse_repository, parse_python_file
from backend.services.graph_service import build_dependency_graph
from backend.services.embedding_service import semantic_search


def _resolve_repo_path(repo_name: str) -> str:
    """Helper to resolve repo_name to an absolute/workspace relative path."""
    if os.path.exists(repo_name):
        return repo_name
    workspace_path = os.path.join("workspace", repo_name)
    if os.path.exists(workspace_path):
        return workspace_path
    return repo_name


def list_repository(repo_name: str) -> dict:
    """Lists repository structure, total files, and language breakdown."""
    repo_path = _resolve_repo_path(repo_name)
    if not os.path.exists(repo_path):
        return {"error": f"Repository path '{repo_path}' does not exist."}
    return scan_repository(repo_path)


def search_code(query: str, top_k: int = 5) -> list:
    """Performs semantic vector search across indexed repository code chunks."""
    try:
        results = semantic_search(query, top_k=top_k)
        return results
    except Exception as e:
        return [{"error": f"Semantic search failed: {str(e)}"}]


def read_file(file_path: str, start_line: int = 1, max_lines: int = 100) -> dict:
    """Reads a section of a file from disk."""
    if not os.path.exists(file_path):
        return {"error": f"File '{file_path}' not found."}
    
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        start_idx = max(0, start_line - 1)
        end_idx = min(total_lines, start_idx + max_lines)
        
        selected_lines = [f"{i+1}: {lines[i]}" for i in range(start_idx, end_idx)]
        
        return {
            "file_path": file_path,
            "total_lines": total_lines,
            "showing_start": start_idx + 1,
            "showing_end": end_idx,
            "content": "".join(selected_lines)
        }
    except Exception as e:
        return {"error": f"Failed to read file '{file_path}': {str(e)}"}


def inspect_symbol(repo_name: str, symbol_name: str) -> dict:
    """Searches AST parsed data for a specific function or class definition across the repository."""
    repo_path = _resolve_repo_path(repo_name)
    parsed = parse_repository(repo_path)
    
    found_definitions = []
    
    for file_data in parsed.get("parsed_files", []):
        file_path = file_data.get("file", "")
        
        if symbol_name in file_data.get("functions", []):
            found_definitions.append({
                "type": "function",
                "symbol": symbol_name,
                "file": file_path
            })
            
        if symbol_name in file_data.get("classes", []):
            found_definitions.append({
                "type": "class",
                "symbol": symbol_name,
                "file": file_path
            })
            
    return {
        "symbol": symbol_name,
        "matches_found": len(found_definitions),
        "definitions": found_definitions
    }


def find_callers(repo_name: str, function_name: str) -> dict:
    """Finds functions in the codebase that invoke the specified function."""
    repo_path = _resolve_repo_path(repo_name)
    parsed = parse_repository(repo_path)
    
    callers = []
    
    for file_data in parsed.get("parsed_files", []):
        file_path = file_data.get("file", "")
        for call_info in file_data.get("function_calls", []):
            caller_func = call_info.get("function")
            called_funcs = call_info.get("calls", [])
            
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


def find_callees(repo_name: str, function_name: str) -> dict:
    """Finds all functions called by the specified function."""
    repo_path = _resolve_repo_path(repo_name)
    parsed = parse_repository(repo_path)
    
    callees = []
    
    for file_data in parsed.get("parsed_files", []):
        file_path = file_data.get("file", "")
        for call_info in file_data.get("function_calls", []):
            caller_func = call_info.get("function")
            if caller_func == function_name:
                for called in call_info.get("calls", []):
                    callees.append({
                        "callee_function": called,
                        "file": file_path
                    })
                    
    return {
        "target_function": function_name,
        "callee_count": len(callees),
        "callees": callees
    }


def find_dependencies(repo_name: str, file_path: str = None) -> dict:
    """Retrieves file import dependencies across the repository or for a specific file."""
    repo_path = _resolve_repo_path(repo_name)
    parsed = parse_repository(repo_path)
    dep_graph = parsed.get("dependency_graph", [])
    
    if file_path:
        for node in dep_graph:
            if node.get("file") == file_path or os.path.basename(node.get("file")) == os.path.basename(file_path):
                return {
                    "file": node.get("file"),
                    "dependencies": node.get("dependencies", [])
                }
        return {"error": f"File '{file_path}' not found in dependency graph."}
        
    return {
        "repository": repo_path,
        "dependency_graph": dep_graph
    }
