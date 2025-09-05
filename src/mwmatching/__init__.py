"""
Algorithm for finding a maximum weight matching in general graphs.
"""

__all__ = ["maximum_weight_matching",
           "adjust_weights_for_maximum_cardinality_matching",
           "MatchingError"]

from .algorithm import (maximum_weight_matching,
                        adjust_weights_for_maximum_cardinality_matching,
                        MatchingError)