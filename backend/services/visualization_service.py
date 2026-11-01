"""
backend/services/visualization_service.py
Generates pyvis dependency graph HTML files.
"""
import os
import networkx as nx
from pyvis.network import Network


def generate_dependency_graph(dependency_graph: list) -> str:
    os.makedirs("backend/static", exist_ok=True)

    graph = nx.DiGraph()
    for item in dependency_graph:
        src = item.get("file", "")
        graph.add_node(src)
        for dep in item.get("dependencies", []):
            graph.add_node(dep)
            graph.add_edge(src, dep)

    net = Network(height="750px", width="100%", directed=True)
    net.from_nx(graph)

    output_path = "backend/static/dependency_graph.html"
    net.save_graph(output_path)
    return output_path