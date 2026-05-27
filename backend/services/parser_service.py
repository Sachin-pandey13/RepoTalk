from tree_sitter import Language, Parser
import tree_sitter_python as tspython
import os

from backend.services.graph_service import build_dependency_graph


PY_LANGUAGE = Language(tspython.language())

parser = Parser(PY_LANGUAGE)


def parse_python_file(file_path: str):

    with open(file_path, "r", encoding="utf-8") as file:
        source_code = file.read()

    tree = parser.parse(bytes(source_code, "utf8"))

    root_node = tree.root_node

    functions = []
    classes = []
    imports = []
    function_calls = []

    for child in root_node.children:

        # Function definitions
        if child.type == "function_definition":

            name_node = child.child_by_field_name("name")

            if name_node:

                function_name = name_node.text.decode()

                functions.append(function_name)

                calls_inside_function = []

                # Recursive traversal for function calls
                def traverse(node):

                    if node.type == "call":

                        called_function = node.child_by_field_name("function")

                        if called_function:

                            calls_inside_function.append(
                                called_function.text.decode()
                            )

                    for child_node in node.children:
                        traverse(child_node)

                traverse(child)

                function_calls.append({
                    "function": function_name,
                    "calls": calls_inside_function
                })

        # Class definitions
        elif child.type == "class_definition":

            name_node = child.child_by_field_name("name")

            if name_node:
                classes.append(name_node.text.decode())

        # Import statements
        elif child.type in ["import_statement", "import_from_statement"]:

            imports.append(child.text.decode())

    return {
        "functions": functions,
        "classes": classes,
        "imports": imports,
        "function_calls": function_calls
    }


def parse_repository(repo_path: str):

    parsed_files = []

    for root, dirs, files in os.walk(repo_path):

        for file in files:

            if file.endswith(".py"):

                file_path = os.path.join(root, file)

                try:

                    parsed_data = parse_python_file(file_path)

                    parsed_files.append({
                        "file": file_path,
                        "functions": parsed_data["functions"],
                        "classes": parsed_data["classes"],
                        "imports": parsed_data["imports"],
                        "function_calls": parsed_data["function_calls"]
                    })

                except Exception as e:

                    parsed_files.append({
                        "file": file_path,
                        "error": str(e)
                    })

    dependency_graph = build_dependency_graph(parsed_files)

    return {
        "repository": repo_path,
        "parsed_files": parsed_files,
        "dependency_graph": dependency_graph
    }