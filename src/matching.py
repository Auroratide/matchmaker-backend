from typing import Sequence
from .mwmatching import maximum_weight_matching

def optimal_matching(edges: Sequence[tuple[int, int, float]]) -> list[tuple[int, int]]:
	return maximum_weight_matching(edges)
