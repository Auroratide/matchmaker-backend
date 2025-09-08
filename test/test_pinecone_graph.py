from src.pinecone_graph import PineconeGraph


INDEX_NAME = "matchmaking-interests"


def test_pinecone_load_pairs_local():
	graph = PineconeGraph(INDEX_NAME)
	graph.build()
	pairs = graph.load_pairs()
	# Seeded by init-local.py: mercury has pastPairings ["venus"]
	assert ("mercury", "venus") in pairs


def test_pinecone_add_pairs_local_and_cleanup():
	graph = PineconeGraph(INDEX_NAME)
	graph.build()

	# Choose two seeded ids that start with empty pastPairings
	a_id, b_id = "jupiter", "saturn"
	assert a_id in graph.id_to_index and b_id in graph.id_to_index

	# Save originals for cleanup
	ai = graph.id_to_index[a_id]
	bi = graph.id_to_index[b_id]
	orig_a_md = dict(graph.vectors[ai].metadata or {})
	orig_b_md = dict(graph.vectors[bi].metadata or {})

	# Act: add pair
	added = graph.add_pairs([(a_id, b_id)])
	assert added == 2

	# Rebuild to observe changes
	graph.build()
	ai2 = graph.id_to_index[a_id]
	bi2 = graph.id_to_index[b_id]
	assert b_id in (graph.vectors[ai2].metadata.get("pastPairings") or [])
	assert a_id in (graph.vectors[bi2].metadata.get("pastPairings") or [])

	# Cleanup: restore original metadata for both ids via bulk upsert
	payload = []
	for vid, md in [(a_id, orig_a_md), (b_id, orig_b_md)]:
		idx = graph.id_to_index[vid]
		payload.append({
			"id": vid,
			"values": graph.vectors[idx].values,
			"metadata": md,
		})
	graph.index.upsert(vectors=payload)
