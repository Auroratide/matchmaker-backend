import math
from src.matching import optimal_matching


def test_maximum_cardinality_even_complete_graph():
	# Build complete graph K6 with positive weights
	edges = []
	for i in range(6):
		for j in range(i + 1, 6):
			w = float(100 - abs(i - j))
			edges.append((i, j, w))

	pairs = optimal_matching(edges)
	# Expect 3 disjoint pairs covering all 6 nodes
	assert len(pairs) == 3
	used = set()
	for a, b in pairs:
		assert a not in used
		assert b not in used
		used.add(a)
		used.add(b)
	assert len(used) == 6


def test_maximum_cardinality_odd_complete_graph():
	edges = []
	for i in range(5):
		for j in range(i + 1, 5):
			w = float(100 - abs(i - j))
			edges.append((i, j, w))

	pairs = optimal_matching(edges)
	# With 5 nodes, expect 2 pairs and 1 unmatched
	assert len(pairs) == 2
	used = set()
	for a, b in pairs:
		assert a not in used
		assert b not in used
		used.add(a)
		used.add(b)
	assert len(used) == 4


def test_isolated_node_without_negative_edges():
	# 4 nodes; node 3 has no edges at all; others form a triangle
	edges = [
		(0, 1, 10.0),
		(0, 2,  9.0),
		(1, 2,  8.0),
	]
	pairs = optimal_matching(edges)
	# One pair, node 3 remains unmatched
	assert len(pairs) == 1
	used = set()
	for a, b in pairs:
		used.add(a)
		used.add(b)
	assert 3 not in used


