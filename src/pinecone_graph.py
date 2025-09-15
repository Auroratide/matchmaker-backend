import os
from typing import TypeVar, Union, Iterable, Optional, Set, Tuple
from pinecone.grpc import PineconeGRPC, GRPCClientConfig, PineconeGrpcFuture
from dotenv import load_dotenv

load_dotenv()

T = TypeVar("T")

class PineconeGraph:
	def __init__(self, index_name):
		self._pinecone_token = os.environ.get("PINECONE_API_KEY")
		self.index_name = index_name
		self.client = PineconeGRPC(
			api_key=self._pinecone_token,
			# host="http://localhost:5080"
		)
		self.id_to_index: dict[str, int] = {}
		self.index_to_id: list[str] = []

	def build(self):
		# index_host = self.client.describe_index(name=self.index_name).host
		# self.index = self.client.Index(host=index_host, grpc_config=GRPCClientConfig(secure=False))
		self.index = self.client.Index(name=self.index_name)

		self.vectors = self.get_all_entries()

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

	def get_all_entries(self):
		"""
		You can't actually grab everything out of Pinecone. You can hack it with a big ol'
		query tho. BIG NOTE THO, this only works for up to 10000 entries.
		"""
		stats = self.index.describe_index_stats()
		dimension = stats["dimension"]
		dummy_vector = [0.0] * dimension

		response = self.gimme(self.index.query(
			vector=dummy_vector,
			top_k=10000,
			include_values=True,
			include_metadata=True
		))

		return response["matches"]

	def load_pairs(self) -> Set[Tuple[str, str]]:
		existing_pairs: Set[Tuple[str, str]] = set()
		for vec in self.vectors:
			past = vec.metadata.get("pastPairings") or []
			for partner_id in past:
				# Coda doesn't wanna insert empty list, so we ignore id 0
				if partner_id == "0" or partner_id == 0:
					continue
				existing_pairs.add((vec.id, partner_id))
		return existing_pairs

	def add_pairs(self, pairs: Iterable[Tuple[str, str]]) -> int:
		partners_to_add: dict[str, set[str]] = {}
		for a, b in pairs:
			partners_to_add.setdefault(a, set()).add(b)
			partners_to_add.setdefault(b, set()).add(a)

		payload = []
		for vid, additions in partners_to_add.items():
			idx = self.id_to_index.get(vid)
			vec = self.vectors[idx]
			metadata = dict(getattr(vec, "metadata", {}) or {})
			past = list(metadata.get("pastPairings") or [])
			metadata["pastPairings"] = list({*past, *additions})
			payload.append({
				"id": vid,
				"values": getattr(vec, "values", []),
				"metadata": metadata,
			})

		if not payload:
			return 0

		self.index.upsert(vectors=payload)
		return len(payload)

	# I dunno why I need this, maybe temporary?
	def gimme(self, thing: Union[T, PineconeGrpcFuture]) -> T:
		if isinstance(thing, PineconeGrpcFuture):
			return thing.result()
		else:
			return thing
