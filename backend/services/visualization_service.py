import networkx as nx
from pyvis.network import Network


def generate_dependency_graph(dependency_graph):

    graph = nx.DiGraph()

    for item in dependency_graph:

        source_file = item["file"]

        graph.add_node(source_file)

        for dependency in item["dependencies"]:

            graph.add_node(dependency)

            graph.add_edge(source_file, dependency)

    net = Network(
        height="750px",
        width="100%",
        directed=True,
        notebook=False
    )

    net.from_nx(graph)

    output_path = "backend/static/dependency_graph.html"

    net.save_graph(output_path)

    return output_path