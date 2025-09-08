from .pinecone_graph import PineconeGraph
from .matching import optimal_matching
from .visualization import visualize_graph
from .coda_client import CodaClient

INDEX_NAME = "matchmaking-interests"
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


### IGNORE EVERYTHING BELOW

# for each vector -> it gets a number
#   get its k-nearest neighbors
#   For each, add it to an edge or whatevers
#   



### OVERALL STUFF.

# extract the people table out of coda
# Also the matches made table? Will be needed to adjust weights between known nodes.

# Need multiple potential algorithm possibilities. But the first will be the "Queen Anne" approach.
#   For each node, get its top K possibilities via ANN
#   ??
# Meaning, we need to extract from the vector database the pairs. The core thing is building the graph.
# OR, use the https://git.jorisvr.nl/joris/maximum-weight-matching thing

# For each pairing, do emails or something, or send to Coda I guess what they are?
# Set this all up to run every once in a while



# Extraction from the graph.

# graph = PineconeGraph().build_graph(edges_per_node) -> I don't need to get all ids, those will come from Coda. We can graph each vector but... maybe not one at a time? Chunk and batch, build the graph gradually.
# pairs = MwMatch().run(graph)
# Do something with pairs
