import networkx as nx
import matplotlib.pyplot as plt

def visualize_graph(edges):
	G = nx.Graph()
	G.add_weighted_edges_from(edges)

	pos = nx.spring_layout(G)  # force-directed layout
	nx.draw(G, pos, with_labels=True, node_color="lightblue", edge_color="gray", node_size=800)
	nx.draw_networkx_edge_labels(G, pos, edge_labels=nx.get_edge_attributes(G, "weight"))
	plt.show()
