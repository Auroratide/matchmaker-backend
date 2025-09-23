from logging import Logger
from .pinecone_graph import PineconeGraph
from .matching import optimal_matching
from .coda_client import CodaClient


INDEX_NAME = "matchmaker-interests-3072"

def perform_matchmaking(logger: Logger):
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

	logger.info("Pairs: ", final_pairs_ids)

	# optionally persist the new pairs
	if new_pairs_ids:
		coda_rows = coda.add_pairs(new_pairs_ids)
		pinecone_vectors = graph.add_pairs(new_pairs_ids)
		logger.info(f"persisted {coda_rows} pairs to Coda; updated {pinecone_vectors} vectors in Pinecone")
