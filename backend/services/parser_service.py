from tree_sitter import Language, Parser
import tree_sitter_python as tspython


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

    for child in root_node.children:

        # Function definitions
        if child.type == "function_definition":

            name_node = child.child_by_field_name("name")

            if name_node:
                functions.append(name_node.text.decode())

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
        "imports": imports
    }