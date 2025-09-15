from .pinecone_graph import PineconeGraph
from .matching import optimal_matching
from .visualization import visualize_graph
from .coda_client import CodaClient

INDEX_NAME = "matchmaker-interests-3072"
# ids_to_grab = ["mercury", "venus", "earth", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto", "eris"]

graph = PineconeGraph(INDEX_NAME)
graph.build()
coda = CodaClient()

existing = graph.load_pairs()
edges = graph.edges(forbidden_pairs=existing)
final_pairs_idx = optimal_matching(edges)

# map index pairs to external ids
final_pairs_ids = [(graph.index_to_id[a], graph.index_to_id[b]) for a, b in final_pairs_idx]

# these are new compared to existing (should already be excluded by forbidden filtering)
new_pairs_ids = [(a, b) for (a, b) in final_pairs_ids if (tuple(sorted((a, b))) not in existing)]

print(edges)
print("final_pairs_ids:", final_pairs_ids)
print("new_pairs_ids (not previously matched):", new_pairs_ids)

visualize_graph(edges)

# optionally persist the new pairs
if new_pairs_ids:
	coda_rows = coda.add_pairs(new_pairs_ids)
	pinecone_vectors = graph.add_pairs(new_pairs_ids)
	print(f"persisted {coda_rows} pairs to Coda; updated {pinecone_vectors} vectors in Pinecone")
