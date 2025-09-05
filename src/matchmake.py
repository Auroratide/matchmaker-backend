from pinecone.grpc import PineconeGRPC, GRPCClientConfig, PineconeGrpcFuture
from typing import TypeVar, Union
from .mwmatching import maximum_weight_matching

T = TypeVar("T")

pinecone = PineconeGRPC(
	api_key="pclocal",
	host="http://localhost:5080"
)

def gimme(thing: Union[T, PineconeGrpcFuture]) -> T:
	if isinstance(thing, PineconeGrpcFuture):
		return thing.result()
	else:
		return thing

INDEX_NAME = "matchmaking-interests"

print("Grabbing all of the doohickeries")
ids_to_grab = ["mercury", "venus", "earth", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto", "eris"]
index_host = pinecone.describe_index(name=INDEX_NAME).host
index = pinecone.Index(host=index_host, grpc_config=GRPCClientConfig(secure=False))

response = index.fetch(ids_to_grab)
vectors = gimme(response).vectors.values()


# example: (1, 3, 0.648923)
edges = []

# Create mapping from vector ID to index for efficient lookup
id_to_index = {vec.id: idx for idx, vec in enumerate(vectors)}

for i, vecy in enumerate(vectors):
	matches = gimme(index.query(
		vector=vecy.values,
		top_k=5,
		include_metadata=False,
	)).matches

	print(vecy.id)
	print(matches)
	
	# Create edges from matches
	for match in matches:
		# Skip self-matches
		if match.id == vecy.id:
			continue
			
		# Find the index of the matched vector
		if match.id in id_to_index:
			match_index = id_to_index[match.id]
			if i < match_index:  # Only add edge in one direction to avoid duplicates
				edges.append((i, match_index, match.score))

print(edges)

matching = maximum_weight_matching(edges)

print(matching)

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
