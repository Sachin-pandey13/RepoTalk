import os


def build_dependency_graph(parsed_files):

    graph = []

    for file_data in parsed_files:

        current_file = file_data["file"]

        imports = file_data.get("imports", [])

        dependencies = []

        for imp in imports:

            # Handle "from x import y"
            if imp.startswith("from"):

                parts = imp.split()

                if len(parts) >= 2:
                    dependencies.append(parts[1])

            # Handle "import x"
            elif imp.startswith("import"):

                parts = imp.split()

                if len(parts) >= 2:
                    dependencies.append(parts[1])

        graph.append({
            "file": current_file,
            "dependencies": dependencies
        })

    return graph