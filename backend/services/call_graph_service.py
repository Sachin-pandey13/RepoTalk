import networkx as nx
from pyvis.network import Network
import os


def generate_call_graph(parsed_files):

    graph = nx.DiGraph()

    for file_data in parsed_files:

        function_calls = file_data.get(
            "function_calls",
            []
        )

        for item in function_calls:

            source_function = item["function"]

            graph.add_node(
                source_function,
                color="orange"
            )

            for called_function in item["calls"]:

                graph.add_node(
                    called_function,
                    color="lightblue"
                )

                graph.add_edge(
                    source_function,
                    called_function
                )

    network = Network(
        height="750px",
        width="100%",
        directed=True,
        bgcolor="#111111",
        font_color="white"
    )

    network.from_nx(graph)

    os.makedirs(
        "backend/static",
        exist_ok=True
    )

    output_path = (
        "backend/static/function_call_graph.html"
    )

    network.save_graph(output_path)

    return output_path