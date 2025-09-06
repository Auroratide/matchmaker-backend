from typing import TypeVar, Union
from pinecone.grpc import PineconeGRPC, GRPCClientConfig, PineconeGrpcFuture

T = TypeVar("T")

class PineconeGraph:
	def __init__(self, index_name):
		self.index_name = index_name
		self.client = PineconeGRPC(
			api_key="pclocal",
			host="http://localhost:5080"
		)

	def build(self, ids_to_grab):
		index_host = self.client.describe_index(name=self.index_name).host
		self.index = self.client.Index(host=index_host, grpc_config=GRPCClientConfig(secure=False))

		response = self.index.fetch(ids_to_grab)
		self.vectors = self.gimme(response).vectors.values()

	def edges(self):
		edges = []

		id_to_index = {vec.id: idx for idx, vec in enumerate(self.vectors)}
		print(id_to_index)

		for i, vecy in enumerate(self.vectors):
			matches = self.gimme(self.index.query(
				vector=vecy.values,
				top_k=5,
				include_metadata=False,
			)).matches

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
		
		return edges
				
	# I dunno why I need this, maybe temporary?
	def gimme(self, thing: Union[T, PineconeGrpcFuture]) -> T:
		if isinstance(thing, PineconeGrpcFuture):
			return thing.result()
		else:
			return thing
