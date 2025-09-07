from typing import Sequence
from .mwmatching import maximum_weight_matching, adjust_weights_for_maximum_cardinality_matching

def optimal_matching(edges: Sequence[tuple[int, int, float]]) -> list[tuple[int, int]]:
	# Prefer maximum-cardinality, then maximum-weight among those
	adjusted = adjust_weights_for_maximum_cardinality_matching(edges)
	return maximum_weight_matching(adjusted)
