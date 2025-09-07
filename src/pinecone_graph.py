from typing import TypeVar, Union, Iterable, Optional, Set, Tuple
from pinecone.grpc import PineconeGRPC, GRPCClientConfig, PineconeGrpcFuture

T = TypeVar("T")

class PineconeGraph:
	def __init__(self, index_name):
		self.index_name = index_name
		self.client = PineconeGRPC(
			api_key="pclocal",
			host="http://localhost:5080"
		)
        self.id_to_index: dict[str, int] = {}
        self.index_to_id: list[str] = []

	def build(self, ids_to_grab):
		index_host = self.client.describe_index(name=self.index_name).host
		self.index = self.client.Index(host=index_host, grpc_config=GRPCClientConfig(secure=False))

		response = self.index.fetch(ids_to_grab)
		self.vectors = list(self.gimme(response).vectors.values())
        # establish mappings between external ids and local indices
        self.id_to_index = {vec.id: idx for idx, vec in enumerate(self.vectors)}
        # preserve ordering using the mapping
        ordered = sorted(self.vectors, key=lambda v: self.id_to_index[v.id])
        self.index_to_id = [v.id for v in ordered]

	def edges(
		self,
		top_k: Optional[int] = None,
		forbidden_pairs: Optional[Set[Tuple[str, str]]] = None,
	):
		edges = []

		id_to_index = self.id_to_index
		print(id_to_index)

		# normalize forbidden pairs to index pairs for quick filtering
		forbidden_idx: Set[Tuple[int, int]] = set()
		if forbidden_pairs:
			for a_id, b_id in forbidden_pairs:
				if a_id in id_to_index and b_id in id_to_index:
					ai = id_to_index[a_id]
					bi = id_to_index[b_id]
					if ai != bi:
						forbidden_idx.add((ai, bi) if ai < bi else (bi, ai))

		requested_top_k = (max(1, top_k) if top_k is not None else max(1, min(50, len(id_to_index) - 1)))

		for i, vecy in enumerate(self.vectors):
			matches = self.gimme(self.index.query(
				vector=vecy.values,
				top_k=requested_top_k,
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
					lo, hi = (i, match_index) if i < match_index else (match_index, i)
					if lo == hi:
						continue
					# Skip forbidden pairs (order-insensitive)
					if (lo, hi) in forbidden_idx:
						continue
					# Only add edge in one direction to avoid duplicates
					if i < match_index:
						edges.append((i, match_index, match.score))
		
		return edges
				
	# I dunno why I need this, maybe temporary?
	def gimme(self, thing: Union[T, PineconeGrpcFuture]) -> T:
		if isinstance(thing, PineconeGrpcFuture):
			return thing.result()
		else:
			return thing
