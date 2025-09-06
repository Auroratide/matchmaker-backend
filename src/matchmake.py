from .pinecone_graph import PineconeGraph
from .matching import optimal_matching
from .visualization import visualize_graph

INDEX_NAME = "matchmaking-interests"
ids_to_grab = ["mercury", "venus", "earth", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto", "eris"]

graph = PineconeGraph(INDEX_NAME)
graph.build(ids_to_grab)

edges = graph.edges()
matching = optimal_matching(edges)

print(edges)
print(matching)

visualize_graph(edges)


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
