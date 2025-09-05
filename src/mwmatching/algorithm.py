"""
Algorithm for finding a maximum weight matching in general graphs.
"""

from __future__ import annotations

import sys
import itertools
import math
from collections.abc import Sequence
from typing import NamedTuple, Optional

from .datastruct import ConcatenableQueue, PriorityQueue


def maximum_weight_matching(
        edges: Sequence[tuple[int, int, float]]
        ) -> list[tuple[int, int]]:
    """Compute a maximum-weighted matching in the general undirected weighted
    graph given by "edges".

    The graph is specified as a list of edges, each edge specified as a tuple
    of its two vertices and the edge weight.
    There may be at most one edge between any pair of vertices.
    No vertex may have an edge to itself.
    The graph may be non-connected (i.e. contain multiple components).

    Vertices are indexed by consecutive, non-negative integers, such that
    the first vertex has index 0 and the last vertex has index (n-1).
    Edge weights may be integers or floating point numbers.

    Isolated vertices (not incident to any edge) are allowed, but not
    recommended since such vertices consume time and memory but have
    no effect on the maximum-weight matching.
    Edges with negative weight are ignored.

    This function takes time O(n * (n + m) * log(n)),
    where "n" is the number of vertices and "m" is the number of edges.
    This function uses O(n + m) memory.

    Parameters:
        edges: List of edges, each edge specified as a tuple "(x, y, w)"
            where "x" and "y" are vertex indices and "w" is the edge weight.

    Returns:
        List of pairs of matched vertex indices.
        This is a subset of the edges in the graph.
        It contains a tuple "(x, y)" if vertex "x" is matched to vertex "y".

    Raises:
        ValueError: If the input does not satisfy the constraints.
        TypeError: If the input contains invalid data types.
        MatchingError: If the matching algorithm fails.
            This can only happen if there is a bug in the algorithm.
    """

    # Check that the input meets all constraints.
    _check_input_types(edges)
    _check_input_graph(edges)

    # Remove edges with negative weight.
    edges = _remove_negative_weight_edges(edges)

    # Special case for empty graphs.
    if not edges:
        return []

    # Initialize graph representation.
    graph = GraphInfo(edges)

    # Initialize the matching algorithm.
    ctx = MatchingContext(graph)
    ctx.start()

    # Improve the solution until no further improvement is possible.
    #
    # Each successful pass through this loop increases the number
    # of matched edges by 1.
    #
    # This loop runs through at most (n/2 + 1) iterations.
    # Each iteration takes time O((n + m) * log(n)).
    while ctx.run_stage():
        pass

    # Extract the final solution.
    ctx.cleanup()
    pairs: list[tuple[int, int]] = [
        (x, y) for (x, y, _w) in edges if ctx.vertex_mate[x] == y]

    # Verify that the matching is optimal.
    # This is just a safeguard; the verification will always pass unless
    # there is a bug in the matching algorithm.
    # Verification only works reliably for integer weights.
    if graph.integer_weights:
        verify_optimum(ctx)

    return pairs


def adjust_weights_for_maximum_cardinality_matching(
        edges: Sequence[tuple[int, int, float]]
        ) -> Sequence[tuple[int, int, float]]:
    """Adjust edge weights such that the maximum-weight matching of
    the adjusted graph is a maximum-cardinality matching, equal to
    a matching in the original graph that has maximum weight out of all
    matchings with maximum cardinality.

    The graph is specified as a list of edges, each edge specified as a tuple
    of its two vertices and the edge weight.
    Edge weights may be integers or floating point numbers.
    Negative edge weights are allowed.

    This function increases all edge weights by an equal amount such that
    the adjusted weights satisfy the following conditions:
     - All edge weights are positive;
     - The minimum edge weight is at least "n" times the difference between
       maximum and minimum edge weight.

    These conditions ensure that a maximum-cardinality matching will be found.
    Proof: The weight of any non-maximum-cardinality matching can be increased
    by matching an additional edge, even if the new edge has minimum edge
    weight and causes all other matched edges to degrade from maximum to
    minimum edge weight.

    Since we are only considering maximum-cardinality matchings, increasing
    all edge weights by an equal amount will not change the set of edges
    that makes up the maximum-weight matching.

    This function increases edge weights by an amount that is proportional
    to the product of the unadjusted weight range and the number of vertices
    in the graph. In case of a big graph with floating point weights, this
    may introduce rounding errors in the weights.

    This function takes time O(m), where "m" is the number of edges.

    Parameters:
        edges: List of edges, each edge specified as a tuple "(x, y, w)"
            where "x" and "y" are vertex indices and "w" is the edge weight.

    Returns:
        List of edges with adjusted weights. If no adjustments are necessary,
        the input list instance may be returned.

    Raises:
        ValueError: If the input does not satisfy the constraints.
        TypeError: If the input contains invalid data types.
    """

    _check_input_types(edges)

    # Don't worry about empty graphs:
    if not edges:
        return edges

    num_vertex = 1 + max(max(x, y) for (x, y, _w) in edges)

    min_weight = min(w for (_x, _y, w) in edges)
    max_weight = max(w for (_x, _y, w) in edges)
    weight_range = max_weight - min_weight

    # Do nothing if the weights already ensure a maximum-cardinality matching.
    if min_weight > 0 and min_weight >= num_vertex * weight_range:
        return edges

    delta: float
    if weight_range > 0:
        # Increase weights to make minimum edge weight large enough
        # to improve any non-maximum-cardinality matching.
        delta = num_vertex * weight_range - min_weight
    else:
        # All weights are the same. Increase weights to make them positive.
        delta = 1 - min_weight

    assert delta >= 0

    # Increase all edge weights by "delta".
    return [(x, y, w + delta) for (x, y, w) in edges]


class MatchingError(Exception):
    """Raised when verification of the matching fails.

    This can only happen if there is a bug in the algorithm.
    """
    pass


def _check_input_types(edges: Sequence[tuple[int, int, float]]) -> None:
    """Check that the input consists of valid data types and valid
    numerical ranges.

    This function takes time O(m).

    Parameters:
        edges: List of edges, each edge specified as a tuple "(x, y, w)"
            where "x" and "y" are edge indices and "w" is the edge weight.

    Raises:
        ValueError: If the input does not satisfy the constraints.
        TypeError: If the input contains invalid data types.
    """

    float_limit = sys.float_info.max / 4

    if not isinstance(edges, list):
        raise TypeError('"edges" must be a list')

    for e in edges:
        if (not isinstance(e, tuple)) or (len(e) != 3):
            raise TypeError("Each edge must be specified as a 3-tuple")

        (x, y, w) = e

        if (not isinstance(x, int)) or (not isinstance(y, int)):
            raise TypeError("Edge endpoints must be integers")

        if (x < 0) or (y < 0):
            raise ValueError("Edge endpoints must be non-negative integers")

        if not isinstance(w, (int, float)):
            raise TypeError(
                "Edge weights must be integers or floating point numbers")

        if isinstance(w, float):
            if not math.isfinite(w):
                raise ValueError("Edge weights must be finite numbers")

            # Check that this edge weight will not cause our dual variable
            # calculations to exceed the valid floating point range.
            if w > float_limit:
                raise ValueError("Floating point edge weights must be"
                                 f" less than {float_limit:g}")


def _check_input_graph(edges: Sequence[tuple[int, int, float]]) -> None:
    """Check that the input is a valid graph, without any multi-edges and
    without any self-edges.

    This function takes time O(m * log(m)).

    Parameters:
        edges: List of edges, each edge specified as a tuple "(x, y, w)"
            where "x" and "y" are edge indices and "w" is the edge weight.

    Raises:
        ValueError: If the input does not satisfy the constraints.
    """

    # Check that the graph has no self-edges.
    for (x, y, _w) in edges:
        if x == y:
            raise ValueError("Self-edges are not supported")

    # Check that the graph does not have multi-edges.
    # Using a set() would be more straightforward, but the runtime bounds
    # of the Python set type are not clearly specified.
    # Sorting provides guaranteed O(m * log(m)) run time.
    edge_endpoints = [((x, y) if (x < y) else (y, x)) for (x, y, _w) in edges]
    edge_endpoints.sort()

    for i in range(len(edge_endpoints) - 1):
        if edge_endpoints[i] == edge_endpoints[i+1]:
            raise ValueError(f"Duplicate edge {edge_endpoints[i]}")


def _remove_negative_weight_edges(
        edges: Sequence[tuple[int, int, float]]
        ) -> Sequence[tuple[int, int, float]]:
    """Remove edges with negative weight.

    This does not change the solution of the maximum-weight matching problem,
    but prevents complications in the algorithm.
    """
    if any(e[2] < 0 for e in edges):
        return [e for e in edges if e[2] >= 0]
    else:
        return edges


class GraphInfo:
    """Representation of the input graph.

    These data remain unchanged while the algorithm runs.
    """

    def __init__(self, edges: Sequence[tuple[int, int, float]]) -> None:
        """Initialize the graph representation and prepare an adjacency list.

        This function takes time O(n + m).
        """

        # Vertices are indexed by integers in range 0 .. n-1.
        # Edges are indexed by integers in range 0 .. m-1.
        #
        # Each edge is incident on two vertices.
        # Each edge also has a weight.
        #
        # "edges[e] = (x, y, w)" where
        #     "e" is an edge index;
        #     "x" and "y" are vertex indices of the incident vertices;
        #     "w" is the edge weight.
        #
        # These data remain unchanged while the algorithm runs.
        self.edges: Sequence[tuple[int, int, float]] = edges

        # num_vertex = the number of vertices.
        if edges:
            self.num_vertex = 1 + max(max(x, y) for (x, y, _w) in edges)
        else:
            self.num_vertex = 0

        # Each vertex is incident to zero or more edges.
        #
        # "adjacent_edges[x]" is the list of edge indices of edges incident
        # to the vertex with index "x".
        #
        # These data remain unchanged while the algorithm runs.
        self.adjacent_edges: list[list[int]] = [
            [] for v in range(self.num_vertex)]
        for (e, (x, y, _w)) in enumerate(edges):
            self.adjacent_edges[x].append(e)
            self.adjacent_edges[y].append(e)

        # Determine whether _all_ weights are integers.
        # In this case we can avoid floating point computations entirely.
        self.integer_weights: bool = all(isinstance(w, int)
                                         for (_x, _y, w) in edges)


# Each vertex may be labeled "S" (outer) or "T" (inner) or be unlabeled.
LABEL_NONE = 0
LABEL_S = 1
LABEL_T = 2


class Blossom:
    """Represents a blossom in a partially matched graph.

    A blossom is an odd-length alternating cycle over sub-blossoms.
    An alternating path consists of alternating matched and unmatched edges.
    An alternating cycle is an alternating path that starts and ends in
    the same sub-blossom.

    Blossoms are recursive structures: A non-trivial blossoms contains
    sub-blossoms, which may themselves contain sub-blossoms etc.

    A single vertex by itself is also a blossom: a "trivial blossom".

    An instance of this class represents either a trivial blossom,
    or a non-trivial blossom.

    Each blossom contains exactly one vertex that is not matched to another
    vertex in the same blossom. This is the "base vertex" of the blossom.
    """

    def __init__(self, base_vertex: int) -> None:
        """Initialize a new blossom."""

        # If this is not a top-level blossom,
        # "parent" is the blossom in which this blossom is a sub-blossom.
        #
        # If this is a top-level blossom,
        # "parent = None".
        self.parent: Optional[NonTrivialBlossom] = None

        # "base_vertex" is the vertex index of the base of the blossom.
        # This is the unique vertex which is contained in the blossom
        # but not matched to another vertex in the same blossom.
        #
        # For trivial blossoms, the base vertex is simply the only
        # vertex in the blossom.
        self.base_vertex: int = base_vertex

        # A top-level blossom that is part of an alternating tree,
        # has label S or T. An unlabeled top-level blossom is not part
        # of any alternating tree.
        self.label: int = LABEL_NONE

        # A labeled top-level blossoms keeps track of the edge through which
        # it is attached to the alternating tree.
        #
        # "tree_edge = (x, y)" if the blossom is attached to an alternating
        # tree via edge "(x, y)" and vertex "y" is contained in the blossom.
        #
        # "tree_edge = None" if the blossom is the root of an alternating tree.
        self.tree_edge: Optional[tuple[int, int]] = None

        # For a labeled top-level blossom,
        # "tree_blossoms" is the set of all top-level blossoms that belong
        # to the same alternating tree. The same set instance is shared by
        # all top-level blossoms in the tree.
        self.tree_blossoms: Optional[set[Blossom]] = None

        # Each top-level blossom maintains a concatenable queue containing
        # all vertices in the blossom.
        self.vertex_queue: ConcatenableQueue[Blossom, int]
        self.vertex_queue = ConcatenableQueue(self)

        # If this is a top-level unlabeled blossom with an edge to an
        # S-blossom, "delta2_node" is the corresponding node in the delta2
        # queue.
        self.delta2_node: Optional[PriorityQueue.Node] = None

        # This variable holds pending lazy updates to the dual variables
        # of the vertices inside the blossom.
        self.vertex_dual_offset: float = 0

        # "marker" is a temporary variable used to discover common
        # ancestors in the alternating tree. It is normally False, except
        # when used by "trace_alternating_paths()".
        self.marker: bool = False

    def vertices(self) -> list[int]:
        """Return a list of vertex indices contained in the blossom."""
        return [self.base_vertex]


class NonTrivialBlossom(Blossom):
    """Represents a non-trivial blossom in a partially matched graph.

    A non-trivial blossom is a blossom that contains multiple sub-blossoms
    (at least 3 sub-blossoms, since all blossoms have odd length).

    Non-trivial blossoms maintain a list of their sub-blossoms and the edges
    between their subblossoms.

    Unlike trivial blossoms, each non-trivial blossom is associated with
    a variable in the dual LPP problem.

    Non-trivial blossoms are created and destroyed by the matching algorithm.
    This implies that not every odd-length alternating cycle is a blossom;
    it only becomes a blossom through an explicit action of the algorithm.
    An existing blossom may change when the matching is augmented along
    a path that runs through the blossom.
    """

    def __init__(
            self,
            subblossoms: list[Blossom],
            edges: list[tuple[int, int]]
            ) -> None:
        """Initialize a new blossom."""

        super().__init__(subblossoms[0].base_vertex)

        # Sanity check.
        n = len(subblossoms)
        assert len(edges) == n
        assert n >= 3
        assert n % 2 == 1

        # "subblossoms" is a list of the sub-blossoms of the blossom,
        # ordered by their appearance in the alternating cycle.
        #
        # "subblossoms[0]" is the start and end of the alternating cycle.
        # "subblossoms[0]" contains the base vertex of the blossom.
        self.subblossoms: list[Blossom] = subblossoms

        # "edges" is a list of edges linking the sub-blossoms.
        # Each edge is represented as an ordered pair "(x, y)" where "x"
        # and "y" are vertex indices.
        #
        # "edges[0] = (x, y)" where vertex "x" in "subblossoms[0]" is
        # adjacent to vertex "y" in "subblossoms[1]", etc.
        self.edges: list[tuple[int, int]] = edges

        # Every non-trivial blossom has a variable in the dual LPP.
        # New blossoms start with dual variable 0.
        #
        # The value of the dual variable changes through delta steps,
        # but these changes are implemented as lazy updates.
        #
        # blossom.dual_var holds the modified blossom dual value.
        # The modified blossom dual is invariant under delta steps.
        #
        # The true dual value of a top-level S-blossom is
        #   blossom.dual_var + ctx.delta_sum_2x
        #
        # The true dual value of a top-level T-blossom is
        #   blossom.dual_var - ctx.delta_sum_2x
        #
        # The true dual value of any other type of blossom is simply
        #   blossom.dual_var
        #
        self.dual_var: float = 0

        # If this is a top-level T-blossom,
        # "delta4_node" is the corresponding node in the delta4 queue.
        # Otherwise "delta4_node" is None.
        self.delta4_node: Optional[PriorityQueue.Node] = None

    def vertices(self) -> list[int]:
        """Return a list of vertex indices contained in the blossom."""

        # Use an explicit stack to avoid deep recursion.
        stack: list[NonTrivialBlossom] = [self]
        nodes: list[int] = []

        while stack:
            b = stack.pop()
            for sub in b.subblossoms:
                if isinstance(sub, NonTrivialBlossom):
                    stack.append(sub)
                else:
                    nodes.append(sub.base_vertex)

        return nodes


class AlternatingPath(NamedTuple):
    """Represents a list of edges forming an alternating path or an
    alternating cycle."""
    edges: list[tuple[int, int]]
    is_cycle: bool


class MatchingContext:
    """Holds all data used by the matching algorithm.

    It contains a partial solution of the matching problem and several
    auxiliary data structures.
    """

    def __init__(self, graph: GraphInfo) -> None:
        """Set up the initial state of the matching algorithm."""

        num_vertex = graph.num_vertex

        # Reference to the input graph.
        # The graph does not change while the algorithm runs.
        self.graph = graph

        # Each vertex is either single (unmatched) or matched to
        # another vertex.
        #
        # If vertex "x" is matched to vertex "y",
        # "vertex_mate[x] == y" and "vertex_mate[y] == x".
        #
        # If vertex "x" is unmatched, "vertex_mate[x] == -1".
        #
        # Initially all vertices are unmatched.
        self.vertex_mate: list[int] = num_vertex * [-1]

        # Each vertex is associated with a trivial blossom.
        # In addition, non-trivial blossoms may be created and destroyed
        # during the course of the matching algorithm.
        #
        # "trivial_blossom[x]" is the trivial blossom that contains only
        # vertex "x".
        self.trivial_blossom: list[Blossom] = [Blossom(x)
                                               for x in range(num_vertex)]

        # Non-trivial blossoms may be created and destroyed during
        # the course of the algorithm.
        #
        # Initially there are no non-trivial blossoms.
        self.nontrivial_blossom: set[NonTrivialBlossom] = set()

        # "vertex_queue_node[x]" represents the vertex "x" inside the
        # concatenable queue of its top-level blossom.
        #
        # Initially, each vertex belongs to its own trivial top-level blossom.
        self.vertex_queue_node = [
            b.vertex_queue.insert(i, math.inf)
            for (i, b) in enumerate(self.trivial_blossom)]

        # All vertex duals are initialized to half the maximum edge weight.
        #
        # "start_vertex_dual_2x" is 2 times the initial vertex dual value.
        #
        # Pre-multiplication by 2 ensures that the values are integers
        # if all edge weights are integers.
        self.start_vertex_dual_2x = max(w for (_x, _y, w) in graph.edges)

        # Every vertex has a variable in the dual LPP.
        #
        # The value of the dual variable changes through delta steps,
        # but these changes are implemented as lazy updates.
        #
        # vertex_dual_2x[x] holds 2 times the modified vertex dual value of
        # vertex "x". The modified vertex dual is invariant under delta steps.
        #
        # The true dual value of an S-vertex is
        #   (vertex_dual_2x[x] - delta_sum_2x) / 2
        #
        # The true dual value of a T-vertex is
        #   (vertex_dual_2x[x] + delta_sum_2x + B(x).vertex_dual_offset) / 2
        #
        # The true dual value of an unlabeled vertex is
        #   (vertex_dual_2x[x] + B(x).vertex_dual_offset) / 2
        #
        self.vertex_dual_2x: list[float]
        self.vertex_dual_2x = num_vertex * [self.start_vertex_dual_2x]

        # Running sum of applied delta steps times 2.
        self.delta_sum_2x: float = 0

        # Queue containing unlabeled top-level blossoms that have an edge to
        # an S-blossom. The priority of a blossom is 2 times its least slack
        # to an S blossom, plus 2 times the running sum of delta steps.
        self.delta2_queue: PriorityQueue[Blossom] = PriorityQueue()

        # Queue containing edges between S-vertices in different top-level
        # blossoms. The priority of an edge is its slack plus 2 times the
        # running sum of delta steps.
        self.delta3_queue: PriorityQueue[int] = PriorityQueue()
        self.delta3_node: list[Optional[PriorityQueue.Node]]
        self.delta3_node = [None for _e in graph.edges]

        # Queue containing top-level non-trivial T-blossoms.
        # The priority of a blossom is its dual plus 2 times the running
        # sum of delta steps.
        self.delta4_queue: PriorityQueue[NonTrivialBlossom] = PriorityQueue()

        # For each T-vertex or unlabeled vertex "x",
        # "vertex_sedge_queue[x]" is a queue of edges between "x" and any
        # S-vertex. The priority of an edge is 2 times its pseudo-slack.
        self.vertex_sedge_queue: list[PriorityQueue[int]]
        self.vertex_sedge_queue = [PriorityQueue() for _x in range(num_vertex)]
        self.vertex_sedge_node: list[Optional[PriorityQueue.Node]]
        self.vertex_sedge_node = [None for _e in graph.edges]

        # Queue of S-vertices to be scanned.
        self.scan_queue: list[int] = []

    def __del__(self) -> None:
        """Delete reference cycles during cleanup of the matching context."""
        for blossom in itertools.chain(self.trivial_blossom,
                                       self.nontrivial_blossom):
            blossom.parent = None
            blossom.vertex_queue.clear()
            del blossom.vertex_queue

    #
    # Find top-level blossom:
    #

    def top_level_blossom(self, x: int) -> Blossom:
        """Find the top-level blossom that contains vertex "x".

        This function takes time O(log(n)).
        """
        return self.vertex_queue_node[x].find()

    #
    # Least-slack edge tracking:
    #

    def edge_pseudo_slack_2x(self, e: int) -> float:
        """Return 2 times the pseudo-slack of the specified edge.

        The pseudo-slack of an edge is related to its true slack, but
        adjusted in a way that makes it invariant under delta steps.

        The true slack of an edge between to S-vertices in different
        top-level blossoms is
          edge_pseudo_slack_2x(e) / 2 - delta_sum_2x

        The true slack of an edge between an S-vertex and an unlabeled
        vertex "y" inside top-level blossom B(y) is
          (edge_pseudo_slack_2x(e)
           - delta_sum_2x + B(y).vertex_dual_offset) / 2
        """
        (x, y, w) = self.graph.edges[e]
        return self.vertex_dual_2x[x] + self.vertex_dual_2x[y] - 2 * w

    def delta2_add_edge(self, e: int, y: int, by: Blossom) -> None:
        """Add edge "e" for delta2 tracking.

        Edge "e" connects an S-vertex to a T-vertex or unlabeled vertex "y".

        This function takes time O(log(n)).
        """

        prio = self.edge_pseudo_slack_2x(e)

        improved = (self.vertex_sedge_queue[y].empty()
                    or (self.vertex_sedge_queue[y].find_min().prio > prio))

        # Insert edge in the S-edge queue of vertex "y".
        assert self.vertex_sedge_node[e] is None
        self.vertex_sedge_node[e] = self.vertex_sedge_queue[y].insert(prio, e)

        # Continue if the new edge becomes the least-slack S-edge for "y".
        if not improved:
            return

        # Update the priority of "y" in its ConcatenableQueue.
        self.vertex_queue_node[y].set_prio(prio)

        # If the blossom is unlabeled and the new edge becomes its least-slack
        # S-edge, insert or update the blossom in the global delta2 queue.
        if by.label == LABEL_NONE:
            prio += by.vertex_dual_offset
            if by.delta2_node is None:
                by.delta2_node = self.delta2_queue.insert(prio, by)
            elif prio < by.delta2_node.prio:
                self.delta2_queue.decrease_prio(by.delta2_node, prio)

    def delta2_remove_edge(self, e: int, y: int, by: Blossom) -> None:
        """Remove edge "e" from delta2 tracking.

        This function is called if an S-vertex becomes unlabeled,
        and edge "e" connects that vertex to vertex "y" which is a T-vertex
        or unlabeled vertex.

        This function takes time O(log(n)).
        """
        vertex_sedge_node = self.vertex_sedge_node[e]
        if vertex_sedge_node is not None:
            # Delete edge from the S-edge queue of vertex "y".
            vertex_sedge_queue = self.vertex_sedge_queue[y]
            vertex_sedge_queue.delete(vertex_sedge_node)
            self.vertex_sedge_node[e] = None

            if vertex_sedge_queue.empty():
                prio = math.inf
            else:
                prio = vertex_sedge_queue.find_min().prio

            # If necessary, update priority of "y" in its ConcatenableQueue.
            if prio > self.vertex_queue_node[y].prio:
                self.vertex_queue_node[y].set_prio(prio)
                if by.label == LABEL_NONE:
                    # Update or delete the blossom in the global delta2 queue.
                    assert by.delta2_node is not None
                    prio = by.vertex_queue.min_prio()
                    if prio < math.inf:
                        prio += by.vertex_dual_offset
                        if prio > by.delta2_node.prio:
                            self.delta2_queue.increase_prio(
                                by.delta2_node, prio)
                    else:
                        self.delta2_queue.delete(by.delta2_node)
                        by.delta2_node = None

    def delta2_enable_blossom(self, blossom: Blossom) -> None:
        """Enable delta2 tracking for "blossom".

        This function is called when a blossom becomes an unlabeled top-level
        blossom. If the blossom has at least one edge to an S-vertex,
        the blossom will be inserted in the global delta2 queue.

        This function takes time O(log(n)).
        """
        assert blossom.delta2_node is None
        prio = blossom.vertex_queue.min_prio()
        if prio < math.inf:
            prio += blossom.vertex_dual_offset
            blossom.delta2_node = self.delta2_queue.insert(prio, blossom)

    def delta2_disable_blossom(self, blossom: Blossom) -> None:
        """Disable delta2 tracking for "blossom".

        The blossom will be removed from the global delta2 queue.
        This function is called when a blossom stops being an unlabeled
        top-level blossom.

        This function takes time O(log(n)).
        """
        if blossom.delta2_node is not None:
            self.delta2_queue.delete(blossom.delta2_node)
            blossom.delta2_node = None

    def delta2_clear_vertex(self, x: int) -> None:
        """Clear delta2 tracking for vertex "x".

        This function is called when "x" becomes an S-vertex.
        It is assumed that the blossom containing "x" has already been
        disabled for delta2 tracking.

        This function takes time O(k + log(n)),
        where "k" is the number of edges incident on "x".
        """
        self.vertex_sedge_queue[x].clear()
        for e in self.graph.adjacent_edges[x]:
            self.vertex_sedge_node[e] = None
        self.vertex_queue_node[x].set_prio(math.inf)

    def delta2_get_min_edge(self) -> tuple[int, float]:
        """Find the least-slack edge between any S-vertex and any unlabeled
        vertex.

        This function takes time O(log(n)).

        Returns:
            Tuple (edge_index, slack_2x) if there is an S-to-unlabeled edge,
            or (-1, Inf) if there is no such edge.
        """

        if self.delta2_queue.empty():
            return (-1, math.inf)

        delta2_node = self.delta2_queue.find_min()
        blossom = delta2_node.data
        prio = delta2_node.prio
        slack_2x = prio - self.delta_sum_2x
        assert blossom.parent is None
        assert blossom.label == LABEL_NONE

        x = blossom.vertex_queue.min_elem()
        e = self.vertex_sedge_queue[x].find_min().data

        return (e, slack_2x)

    def delta3_add_edge(self, e: int) -> None:
        """Add edge "e" for delta3 tracking.

        This function is called if a vertex becomes an S-vertex and edge "e"
        connects it to an S-vertex in a different top-level blossom.

        This function takes time O(log(n)).
        """
        # The edge may already be in the delta3 queue, if it was previously
        # discovered in the opposite direction.
        if self.delta3_node[e] is None:
            # Priority is edge slack plus 2 times the running sum of
            # delta steps.
            prio_2x = self.edge_pseudo_slack_2x(e)
            if self.graph.integer_weights:
                # If all edge weights are integers, the slack of
                # any edge between S-vertices is also an integer.
                assert prio_2x % 2 == 0
                prio = prio_2x // 2
            else:
                prio = prio_2x / 2
            self.delta3_node[e] = self.delta3_queue.insert(prio, e)

    def delta3_remove_edge(self, e: int) -> None:
        """Remove edge "e" from delta3 tracking.

        This function is called if a former S-vertex becomes unlabeled,
        and edge "e" connects it to another S-vertex.

        This function takes time O(log(n)).
        """
        delta3_node = self.delta3_node[e]
        if delta3_node is not None:
            self.delta3_queue.delete(delta3_node)
            self.delta3_node[e] = None

    def delta3_get_min_edge(self) -> tuple[int, float]:
        """Find the least-slack edge between any pair of S-vertices in
        different top-level blossoms.

        This function takes time O(1 + k * log(n)),
        where "k" is the number of intra-blossom edges removed from the queue.

        Returns:
            Tuple (edge_index, slack) if there is an S-to-S edge,
            or (-1, Inf) if there is no suitable edge.
        """
        while not self.delta3_queue.empty():
            delta3_node = self.delta3_queue.find_min()
            e = delta3_node.data
            (x, y, _w) = self.graph.edges[e]
            bx = self.top_level_blossom(x)
            by = self.top_level_blossom(y)
            assert (bx.label == LABEL_S) and (by.label == LABEL_S)
            if bx is not by:
                slack = delta3_node.prio - self.delta_sum_2x
                return (e, slack)

            # Reject edges between vertices within the same top-level blossom.
            # Although intra-blossom edges are never inserted into the queue,
            # existing edges in the queue may become intra-blossom when
            # a new blossom is formed.
            self.delta3_queue.delete(delta3_node)
            self.delta3_node[e] = None

        # If the queue is empty, no suitable edge exists.
        return (-1, math.inf)

    #
    # Managing blossom labels:
    #

    def assign_blossom_label_s(self, blossom: Blossom) -> None:
        """Change an unlabeled top-level blossom into an S-blossom.

        For a blossom with "j" vertices and "k" incident edges,
        this function takes time O(j * log(n) + k).

        This function is called at most once per blossom per stage.
        It therefore takes total time O(n * log(n) + m) per stage.
        """

        assert blossom.parent is None
        assert blossom.label == LABEL_NONE
        blossom.label = LABEL_S

        # Labeled blossoms must not be in the delta2 queue.
        self.delta2_disable_blossom(blossom)

        # Adjust for lazy updating of S-blossom dual variables.
        #
        # The true dual value of an unlabeled top-level blossom is
        #   blossom.dual_var
        #
        # while the true dual value of a top-level S-blossom is
        #   blossom.dual_var + ctx.delta_sum_2x
        #
        # The value of blossom.dual_var must be adjusted accordingly
        # when the blossom changes from unlabeled to S-blossom.
        #
        if isinstance(blossom, NonTrivialBlossom):
            blossom.dual_var -= self.delta_sum_2x

        # Apply pending updates to vertex dual variables and prepare
        # for lazy updating of S-vertex dual variables.
        #
        # For S-blossoms, blossom.vertex_dual_offset is always 0.
        #
        # Furthermore, the true dual value of an unlabeled vertex is
        #   (vertex_dual_2x[x] + blossom.vertex_dual_offset) / 2
        #
        # while the true dual value of an S-vertex is
        #   (vertex_dual_2x[x] - delta_sum_2x) / 2
        #
        # The value of vertex_dual_2x must be adjusted accordingly
        # when vertices change from unlabeled to S-vertex.
        #
        vertex_dual_fixup = self.delta_sum_2x + blossom.vertex_dual_offset
        blossom.vertex_dual_offset = 0
        vertices = blossom.vertices()
        for x in vertices:
            self.vertex_dual_2x[x] += vertex_dual_fixup

            # S-vertices do not keep track of potential delta2 edges.
            self.delta2_clear_vertex(x)

        # Add the new S-vertices to the scan queue.
        self.scan_queue.extend(vertices)

    def assign_blossom_label_t(self, blossom: Blossom) -> None:
        """Change an unlabeled top-level blossom into a T-blossom.

        This function takes time O(log(n)).
        """

        assert blossom.parent is None
        assert blossom.label == LABEL_NONE
        blossom.label = LABEL_T

        # Labeled blossoms must not be in the delta2 queue.
        self.delta2_disable_blossom(blossom)

        if isinstance(blossom, NonTrivialBlossom):

            # Adjust for lazy updating of T-blossom dual variables.
            #
            # The true dual value of an unlabeled top-level blossom is
            #   blossom.dual_var
            #
            # while the true dual value of a top-level T-blossom is
            #   blossom.dual_var - ctx.delta_sum_2x
            #
            # The value of blossom.dual_var must be adjusted accordingly
            # when the blossom changes from unlabeled to S-blossom.
            #
            blossom.dual_var += self.delta_sum_2x

            # Top-level T-blossoms are tracked in the delta4 queue.
            assert blossom.delta4_node is None
            blossom.delta4_node = self.delta4_queue.insert(blossom.dual_var,
                                                           blossom)

        # Prepare for lazy updating of T-vertex dual variables.
        #
        # The true dual value of an unlabeled vertex is
        #  (vertex_dual_2x[x] + blossom.vertex_dual_offset) / 2
        #
        # while the true dual value of a T-vertex is
        #  (vertex_dual_2x[x] + blossom.vertex_dual_offset + delta_sum_2x) / 2
        #
        # The value of blossom.vertex_dual_offset must be adjusted accordingly
        # when the blossom changes from unlabeled to T-blossom.
        #
        blossom.vertex_dual_offset -= self.delta_sum_2x

    def remove_blossom_label_s(self, blossom: Blossom) -> None:
        """Change a top-level S-blossom into an unlabeled blossom.

        For a blossom with "j" vertices and "k" incident edges,
        this function takes time O((j + k) * log(n)).

        This function is called at most once per blossom per stage.
        It therefore takes total time O((n + m) * log(n)) per stage.
        """

        assert blossom.parent is None
        assert blossom.label == LABEL_S
        blossom.label = LABEL_NONE

        # Unwind lazy delta updates to the S-blossom dual variable.
        if isinstance(blossom, NonTrivialBlossom):
            blossom.dual_var += self.delta_sum_2x

        assert blossom.vertex_dual_offset == 0
        vertex_dual_fixup = -self.delta_sum_2x

        edges = self.graph.edges
        adjacent_edges = self.graph.adjacent_edges

        for x in blossom.vertices():

            # Unwind lazy delta updates to S-vertex dual variables.
            self.vertex_dual_2x[x] += vertex_dual_fixup

            # Scan the incident edges of all vertices in the blossom.
            for e in adjacent_edges[x]:
                (p, q, _w) = edges[e]
                y = p if p != x else q

                # If this edge is in the delta3 queue, remove it.
                # Only edges between S-vertices are tracked for delta3,
                # and vertex "x" is no longer an S-vertex.
                self.delta3_remove_edge(e)

                by = self.top_level_blossom(y)
                if by.label == LABEL_S:
                    # Edge "e" connects unlabeled vertex "x" to S-vertex "y".
                    # It must be tracked for delta2 via vertex "x".
                    self.delta2_add_edge(e, x, blossom)
                else:
                    # Edge "e" connects former S-vertex "x" to T-vertex
                    # or unlabeled vertex "y". That implies this edge was
                    # tracked for delta2 via vertex "y", but it must be
                    # removed now.
                    self.delta2_remove_edge(e, y, by)

    def remove_blossom_label_t(self, blossom: Blossom) -> None:
        """Change a top-level T-blossom into an unlabeled blossom.

        This function takes time O(log(n)).
        """

        assert blossom.parent is None
        assert blossom.label == LABEL_T
        blossom.label = LABEL_NONE

        if isinstance(blossom, NonTrivialBlossom):

            # Unlabeled blossoms are not tracked in the delta4 queue.
            assert blossom.delta4_node is not None
            self.delta4_queue.delete(blossom.delta4_node)
            blossom.delta4_node = None

            # Unwind lazy updates to the T-blossom dual variable.
            blossom.dual_var -= self.delta_sum_2x

        # Unwind lazy updates of T-vertex dual variables.
        blossom.vertex_dual_offset += self.delta_sum_2x

        # Enable unlabeled top-level blossom for delta2 tracking.
        self.delta2_enable_blossom(blossom)

    def change_s_blossom_to_subblossom(self, blossom: Blossom) -> None:
        """Change a top-level S-blossom into an S-subblossom.

        This function takes time O(1).
        """

        assert blossom.parent is None
        assert blossom.label == LABEL_S
        blossom.label = LABEL_NONE

        # Unwind lazy delta updates to the S-blossom dual variable.
        if isinstance(blossom, NonTrivialBlossom):
            blossom.dual_var += self.delta_sum_2x

    #
    # General support routines:
    #

    def reset_blossom_label(self, blossom: Blossom) -> None:
        """Remove blossom label."""

        assert blossom.parent is None
        assert blossom.label != LABEL_NONE

        if blossom.label == LABEL_S:
            self.remove_blossom_label_s(blossom)
        else:
            self.remove_blossom_label_t(blossom)

    def remove_alternating_tree(self, tree_blossoms: set[Blossom]) -> None:
        """Reset the alternating tree consisting of the specified blossoms.

        Marks the blossoms as unlabeled.
        Updates delta tracking accordingly.

        This function takes time O((n + m) * log(n)).
        """
        for blossom in tree_blossoms:
            assert blossom.label != LABEL_NONE
            assert blossom.tree_blossoms is tree_blossoms
            self.reset_blossom_label(blossom)
            blossom.tree_edge = None
            blossom.tree_blossoms = None

    def trace_alternating_paths(self, x: int, y: int) -> AlternatingPath:
        """Trace back through the alternating trees from vertices "x" and "y".

        If both vertices are part of the same alternating tree, this function
        discovers a new blossom. In this case it returns an alternating path
        through the blossom that starts and ends in the same sub-blossom.

        If the vertices are part of different alternating trees, this function
        discovers an augmenting path. In this case it returns an alternating
        path that starts and ends in an unmatched vertex.

        This function takes time O(k * log(n)) to discover a blossom,
        where "k" is the number of sub-blossoms,
        or time O(n * log(n)) to discover an augmenting path.

        Returns:
            Alternating path as an ordered list of edges between top-level
            blossoms.
        """

        marked_blossoms: list[Blossom] = []

        # "xedges" is a list of edges used while tracing from "x".
        # "yedges" is a list of edges used while tracing from "y".
        # Pre-load the edge (x, y) on both lists.
        xedges: list[tuple[int, int]] = [(x, y)]
        yedges: list[tuple[int, int]] = [(y, x)]

        # "first_common" is the first common ancestor of "x" and "y"
        # in the alternating tree, or None if there is no common ancestor.
        first_common: Optional[Blossom] = None

        # Alternate between tracing the path from "x" and the path from "y".
        # This ensures that the search time is bounded by the size of the
        # newly found blossom.
        while x != -1 or y != -1:

            # Check if we found a common ancestor.
            bx = self.top_level_blossom(x)
            if bx.marker:
                first_common = bx
                break

            # Mark blossom as a potential common ancestor.
            bx.marker = True
            marked_blossoms.append(bx)

            # Track back through the link in the alternating tree.
            if bx.tree_edge is None:
                # Reached the root of this alternating tree.
                x = -1
            else:
                xedges.append(bx.tree_edge)
                x = bx.tree_edge[0]

            # Swap "x" and "y" to alternate between paths.
            if y != -1:
                (x, y) = (y, x)
                (xedges, yedges) = (yedges, xedges)

        # Remove all markers we placed.
        for b in marked_blossoms:
            b.marker = False

        # If we found a common ancestor, trim the paths so they end there.
        if first_common is not None:
            assert self.top_level_blossom(xedges[-1][0]) is first_common
            while (self.top_level_blossom(yedges[-1][0])
                   is not first_common):
                yedges.pop()

        # Fuse the two paths.
        # Flip the order of one path, and flip the edge tuples in the other
        # path to obtain a continuous path with correctly ordered edge tuples.
        # Skip the duplicate edge in one of the paths.
        path_edges = xedges[::-1] + [(y, x) for (x, y) in yedges[1:]]

        # Any S-to-S alternating path must have odd length.
        assert len(path_edges) % 2 == 1

        return AlternatingPath(edges=path_edges,
                               is_cycle=(first_common is not None))

    #
    # Merge and expand blossoms:
    #

    def make_blossom(self, path: AlternatingPath) -> None:
        """Create a new blossom from an alternating cycle.

        Assign label S to the new blossom.
        Relabel all T-sub-blossoms as S and add their vertices to the queue.

        A blossom will not be expanded during the same stage in which
        it was created.

        This function takes total time O((n + m) * log(n)) per stage.
        """

        # Check that the path is odd-length.
        assert len(path.edges) % 2 == 1
        assert len(path.edges) >= 3

        # Construct the list of sub-blossoms (current top-level blossoms).
        subblossoms = [self.top_level_blossom(x) for (x, y) in path.edges]

        # Check that the path is cyclic.
        # Note the path will not always start and end with the same _vertex_,
        # but it must start and end in the same _blossom_.
        subblossoms_next = [self.top_level_blossom(y)
                            for (x, y) in path.edges]
        assert subblossoms[0] == subblossoms_next[-1]
        assert subblossoms[1:] == subblossoms_next[:-1]

        # Blossom must start and end with an S-sub-blossom.
        assert subblossoms[0].label == LABEL_S

        # Remove blossom labels.
        # Mark vertices inside former T-blossoms as S-vertices.
        for sub in subblossoms:
            if sub.label == LABEL_T:
                self.remove_blossom_label_t(sub)
                self.assign_blossom_label_s(sub)
            self.change_s_blossom_to_subblossom(sub)

        # Create the new blossom object.
        blossom = NonTrivialBlossom(subblossoms, path.edges)

        # Assign label S to the new blossom.
        blossom.label = LABEL_S

        # Prepare for lazy updating of S-blossom dual variable.
        blossom.dual_var = -self.delta_sum_2x

        # Link the new blossom to the alternating tree.
        tree_blossoms = subblossoms[0].tree_blossoms
        assert tree_blossoms is not None
        blossom.tree_edge = subblossoms[0].tree_edge
        blossom.tree_blossoms = tree_blossoms
        tree_blossoms.add(blossom)

        # Add to the list of blossoms.
        self.nontrivial_blossom.add(blossom)

        # Link the subblossoms to the their new parent.
        for sub in subblossoms:
            sub.parent = blossom

            # Remove subblossom from the alternating tree.
            sub.tree_edge = None
            sub.tree_blossoms = None
            tree_blossoms.remove(sub)

        # Merge concatenable queues.
        blossom.vertex_queue.merge([sub.vertex_queue for sub in subblossoms])

    @staticmethod
    def find_path_through_blossom(
            blossom: NonTrivialBlossom,
            sub: Blossom
            ) -> tuple[list[Blossom], list[tuple[int, int]]]:
        """Construct a path with an even number of edges through the
        specified blossom, from sub-blossom "sub" to the base of "blossom".

        Return:
            Tuple (nodes, edges).
        """

        # Walk around the blossom from "sub" to its base.
        p = blossom.subblossoms.index(sub)
        if p % 2 == 0:
            # Walk backwards around the blossom.
            # Flip edges from (i,j) to (j,i) to make them fit
            # in the path from "sub" to base.
            nodes = blossom.subblossoms[p::-1]
            edges = [(j, i) for (i, j) in blossom.edges[:p][::-1]]
        else:
            # Walk forward around the blossom.
            nodes = blossom.subblossoms[p:] + blossom.subblossoms[0:1]
            edges = blossom.edges[p:]

        assert len(edges) % 2 == 0
        assert len(nodes) % 2 == 1

        return (nodes, edges)

    def expand_unlabeled_blossom(self, blossom: NonTrivialBlossom) -> None:
        """Expand the specified unlabeled blossom.

        This function takes total time O(n * log(n)) per stage.
        """

        assert blossom.parent is None
        assert blossom.label == LABEL_NONE

        # Remove blossom from the delta2 queue.
        self.delta2_disable_blossom(blossom)

        # Split concatenable queue.
        blossom.vertex_queue.split()

        # Prepare to push lazy delta updates down to the sub-blossoms.
        vertex_dual_offset = blossom.vertex_dual_offset
        blossom.vertex_dual_offset = 0

        # Convert sub-blossoms into top-level blossoms.
        for sub in blossom.subblossoms:
            assert sub.label == LABEL_NONE
            sub.parent = None

            assert sub.vertex_dual_offset == 0
            sub.vertex_dual_offset = vertex_dual_offset

            self.delta2_enable_blossom(sub)

        # Avoid leaking a reference cycle.
        del blossom.vertex_queue

        # Delete the expanded blossom.
        self.nontrivial_blossom.remove(blossom)

    def expand_t_blossom(self, blossom: NonTrivialBlossom) -> None:
        """Expand the specified T-blossom.

        This function takes total time O(n * log(n) + m) per stage.
        """

        assert blossom.parent is None
        assert blossom.label == LABEL_T
        assert blossom.delta2_node is None

        # Remove blossom from its alternating tree.
        tree_blossoms = blossom.tree_blossoms
        assert tree_blossoms is not None
        tree_blossoms.remove(blossom)

        # Remove label T.
        self.remove_blossom_label_t(blossom)

        # Expand the now-unlabeled blossom.
        self.expand_unlabeled_blossom(blossom)

        # The expanded blossom was part of an alternating tree, linked to
        # a parent node in the tree via one of its subblossoms, and linked to
        # a child node of the tree via the base vertex.
        # We must reconstruct this part of the alternating tree, which will
        # now run via sub-blossoms of the expanded blossom.

        # Find the sub-blossom that is attached to the parent node in
        # the alternating tree.
        assert blossom.tree_edge is not None
        (x, y) = blossom.tree_edge
        sub = self.top_level_blossom(y)

        # Assign label T to that sub-blossom.
        self.assign_blossom_label_t(sub)
        sub.tree_edge = blossom.tree_edge
        sub.tree_blossoms = tree_blossoms
        tree_blossoms.add(sub)

        # Walk through the expanded blossom from "sub" to the base vertex.
        # Assign alternating S and T labels to the sub-blossoms and attach
        # them to the alternating tree.
        (path_nodes, path_edges) = self.find_path_through_blossom(blossom,
                                                                  sub)

        for p in range(0, len(path_edges), 2):
            #
            #   (p) ==(y,x)== (p+1) ----- (p+2)
            #    T              S           T
            #
            # path_nodes[p] has already been labeled T.
            # We now assign labels to path_nodes[p+1] and path_nodes[p+2].

            # Assign label S to path_nodes[p+1].
            (y, x) = path_edges[p]
            self.extend_tree_t_to_s(x)

            # Assign label T to path_nodes[i+2] and attach it
            # to path_nodes[p+1].
            sub = path_nodes[p+2]
            self.assign_blossom_label_t(sub)
            sub.tree_edge = path_edges[p+1]
            sub.tree_blossoms = tree_blossoms
            tree_blossoms.add(sub)

    #
    # Augmenting:
    #

    def augment_blossom_rec(
            self,
            blossom: NonTrivialBlossom,
            sub: Blossom,
            stack: list[tuple[NonTrivialBlossom, Blossom]]
            ) -> None:
        """Augment along an alternating path through the specified blossom,
        from sub-blossom "sub" to the base vertex of the blossom.

        Modify the blossom to reflect that sub-blossom "sub" contains
        the base vertex after augmenting.

        Mark any sub-blossoms on the alternating path for recursive
        augmentation, except for sub-blossom "sub" which has already been
        augmented. Use the stack instead of making direct recursive calls.
        """

        # Walk through the blossom from "sub" to the base vertex.
        (path_nodes, path_edges) = self.find_path_through_blossom(blossom,
                                                                  sub)

        for p in range(0, len(path_edges), 2):
            # Before augmentation:
            #   path_nodes[p] is matched to path_nodes[p+1]
            #
            #   (p) ===== (p+1) ---(x,y)--- (p+2)
            #
            # After augmentation:
            #   path_nodes[p+1] matched to path_nodes[p+2] via edge (i,j)
            #
            #   (p) ----- (p+1) ===(x,y)=== (p+2)
            #

            # Pull the edge (x, y) into the matching.
            (x, y) = path_edges[p+1]
            self.vertex_mate[x] = y
            self.vertex_mate[y] = x

            # Augment through the subblossoms touching the edge (x, y).
            # Nothing needs to be done for trivial subblossoms.
            bx = path_nodes[p+1]
            if isinstance(bx, NonTrivialBlossom):
                stack.append((bx, self.trivial_blossom[x]))

            by = path_nodes[p+2]
            if isinstance(by, NonTrivialBlossom):
                stack.append((by, self.trivial_blossom[y]))

        # Rotate the subblossom list so the new base ends up in position 0.
        p = blossom.subblossoms.index(sub)
        blossom.subblossoms = (
            blossom.subblossoms[p:] + blossom.subblossoms[:p])
        blossom.edges = blossom.edges[p:] + blossom.edges[:p]

        # Update the base vertex.
        # We can pull this from the sub-blossom where we started since
        # its augmentation has already finished.
        blossom.base_vertex = sub.base_vertex

    def augment_blossom(
            self,
            blossom: NonTrivialBlossom,
            sub: Blossom
            ) -> None:
        """Augment along an alternating path through the specified blossom,
        from sub-blossom "sub" to the base vertex of the blossom.

        Recursively augment any sub-blossoms on the alternating path.

        This function takes time O(n).
        """

        # Use an explicit stack to avoid deep recursion.
        stack = [(blossom, sub)]

        while stack:
            (outer_blossom, sub) = stack.pop()
            assert sub.parent is not None
            blossom = sub.parent

            if blossom != outer_blossom:
                # Sub-blossom "sub" is an indirect (nested) child of
                # the "outer_blossom" we are supposed to be augmenting.
                #
                # "blossom" is the direct parent of "sub".
                # Let's first augment "blossom" from "sub" to its base vertex.
                # Then continue by augmenting the parent of "blossom",
                # from "blossom" to its base vertex, and so on until we
                # get to the "outer_blossom".
                #
                # Set up to continue augmenting through the parent of
                # "blossom".
                stack.append((outer_blossom, blossom))

            # Augment "blossom" from "sub" to the base vertex.
            self.augment_blossom_rec(blossom, sub, stack)

    def augment_matching(self, path: AlternatingPath) -> None:
        """Augment the matching through the specified augmenting path.

        This function takes time O(n * log(n)).
        """

        # Check that the augmenting path starts and ends in
        # an unmatched vertex or a blossom with unmatched base.
        assert len(path.edges) % 2 == 1
        for x in (path.edges[0][0], path.edges[-1][1]):
            b = self.top_level_blossom(x)
            assert self.vertex_mate[b.base_vertex] == -1

        # The augmenting path looks like this:
        #
        #   (unmatched) ---- (B) ==== (B) ---- (B) ==== (B) ---- (unmatched)
        #
        # The first and last vertex (or blossom) of the path are unmatched
        # (or have unmatched base vertex). After augmenting, those vertices
        # will be matched. All matched edges on the path become unmatched,
        # and unmatched edges become matched.
        #
        # This loop walks along the edges of this path that were not matched
        # before augmenting.
        for (x, y) in path.edges[0::2]:

            # Augment the non-trivial blossoms on either side of this edge.
            # No action is necessary for trivial blossoms.
            bx = self.top_level_blossom(x)
            if isinstance(bx, NonTrivialBlossom):
                self.augment_blossom(bx, self.trivial_blossom[x])

            by = self.top_level_blossom(y)
            if isinstance(by, NonTrivialBlossom):
                self.augment_blossom(by, self.trivial_blossom[y])

            # Pull the edge into the matching.
            self.vertex_mate[x] = y
            self.vertex_mate[y] = x

    #
    # Alternating tree:
    #

    def extend_tree_t_to_s(self, x: int) -> None:
        """Assign label S to the unlabeled blossom that contains vertex "x".

        The newly labeled S-blossom is added to the alternating tree
        via its matched edge. All vertices in the newly labeled S-blossom
        are added to the scan queue.

        Preconditions:
         - "x" is a vertex in an unlabeled blossom.
         - "x" is matched to a T-vertex via a tight edge.
        """

        # Assign label S to the blossom that contains vertex "x".
        bx = self.top_level_blossom(x)
        self.assign_blossom_label_s(bx)

        # Vertex "x" is matched to T-vertex "y".
        y = self.vertex_mate[x]
        assert y != -1

        by = self.top_level_blossom(y)
        assert by.label == LABEL_T
        assert by.tree_blossoms is not None

        # Attach the blossom that contains "x" to the alternating tree.
        bx.tree_edge = (y, x)
        bx.tree_blossoms = by.tree_blossoms
        bx.tree_blossoms.add(bx)

    def extend_tree_s_to_t(self, x: int, y: int) -> None:
        """Assign label T to the unlabeled blossom that contains vertex "y".

        The newly labeled T-blossom is added to the alternating tree.
        Directly afterwards, label S is assigned to the blossom that has
        a matched edge to the base of the newly labeled T-blossom, and
        that newly labeled S-blossom is also added to the alternating tree.

        Preconditions:
         - "x" is an S-vertex.
         - "y" is a vertex in an unlabeled blossom with a matched base vertex.
         - There is a tight edge between vertices "x" and "y".
        """

        bx = self.top_level_blossom(x)
        by = self.top_level_blossom(y)
        assert bx.label == LABEL_S

        # Expand zero-dual blossoms before assigning label T.
        while isinstance(by, NonTrivialBlossom) and (by.dual_var == 0):
            self.expand_unlabeled_blossom(by)
            by = self.top_level_blossom(y)

        # Assign label T to the unlabeled blossom.
        self.assign_blossom_label_t(by)
        by.tree_edge = (x, y)
        by.tree_blossoms = bx.tree_blossoms
        assert by.tree_blossoms is not None
        by.tree_blossoms.add(by)

        # Assign label S to the blossom that is mated to the T-blossom.
        z = self.vertex_mate[by.base_vertex]
        assert z != -1
        self.extend_tree_t_to_s(z)

    def add_s_to_s_edge(self, x: int, y: int) -> bool:
        """Add the edge between S-vertices "x" and "y".

        If the edge connects blossoms that are part of the same alternating
        tree, this function creates a new S-blossom and returns False.

        If the edge connects two different alternating trees, an augmenting
        path has been discovered. This function then augments the matching
        and returns True. Labels are removed from blossoms that belonged
        to the two alternating trees involved in the matching. All other
        alternating trees and labels are preserved.

        Preconditions:
         - "x" and "y" are S-vertices in different top-level blossoms.
         - There is a tight edge between vertices "x" and "y".

        Returns:
            True if the matching was augmented; otherwise False.
        """

        bx = self.top_level_blossom(x)
        by = self.top_level_blossom(y)

        assert bx.label == LABEL_S
        assert by.label == LABEL_S
        assert bx is not by

        # Trace back through the alternating trees from "x" and "y".
        path = self.trace_alternating_paths(x, y)

        assert bx.tree_blossoms is not None
        assert by.tree_blossoms is not None

        if bx.tree_blossoms is by.tree_blossoms:
            # Both blossoms belong to the same alternating tree.
            # This implies that the alternating path is a cycle.
            # The path will be used to create a new blossom.
            assert path.is_cycle
            self.make_blossom(path)

            return False

        else:
            # The blossoms belong to different alternating trees.
            # This implies that the alternating path is an augmenting
            # path between two unlabeled vertices.
            # The path will be used to augment the matching.

            # Delete the two alternating trees on the augmenting path.
            # The blossoms in those trees become unlabeled.
            self.remove_alternating_tree(bx.tree_blossoms)
            self.remove_alternating_tree(by.tree_blossoms)

            # Augment the matching.
            assert not path.is_cycle
            self.augment_matching(path)

            return True

    def scan_new_s_vertices(self) -> None:
        """Scan the incident edges of newly labeled S-vertices.

        Edges are added to delta2 tracking or delta3 tracking depending
        on the state of the vertex on the opposite side of the edge.

        This function does not yet use the edges to extend the alternating
        tree or find blossoms or augmenting paths, even if the edges
        are tight. If there are such tight edges, they will be used later
        through zero-delta steps.

        If there are "j" new S-vertices with a total of "k" incident edges,
        this function takes time O((j + k) * log(n)).

        Since each vertex can become an S-vertex at most once per stage,
        this function takes total time O((n + m) * log(n)) per stage.
        """

        edges = self.graph.edges
        adjacent_edges = self.graph.adjacent_edges

        # Process S-vertices waiting to be scanned.
        # This loop runs through O(n) iterations per stage.
        for x in self.scan_queue:

            # Double-check that "x" is an S-vertex.
            bx = self.top_level_blossom(x)
            assert bx.label == LABEL_S

            # Scan the edges that are incident on "x".
            # This loop runs through O(m) iterations per stage.
            for e in adjacent_edges[x]:
                (p, q, _w) = edges[e]
                y = p if p != x else q

                # Ignore edges that are internal to a blossom.
                by = self.top_level_blossom(y)
                if bx is by:
                    continue

                if by.label == LABEL_S:
                    # Edge between S-vertices.
                    self.delta3_add_edge(e)
                else:
                    # Edge to T-vertex or unlabeled vertex.
                    self.delta2_add_edge(e, y, by)

        self.scan_queue.clear()

    #
    # Delta steps:
    #

    def calc_dual_delta_step(
            self
            ) -> tuple[int, float, int, Optional[NonTrivialBlossom]]:
        """Calculate a delta step in the dual LPP problem.

        This function returns the minimum of the 4 types of delta values,
        and the type of delta which obtain the minimum, and the edge or
        blossom that produces the minimum delta, if applicable.

        The returned value is 2 times the actual delta value.
        Multiplication by 2 ensures that the result is an integer if all edge
        weights are integers.

        This function takes time O((1 + k) * log(n)),
        where "k" is the number of intra-blossom edges removed from
        the delta3 queue.

        At most O(n) delta steps can occur during a stage.
        Each edge can be inserted into the delta3 queue at most once per stage.
        Therefore, this function takes total time O((n + m) * log(n))
        per stage.

        Returns:
            Tuple (delta_type, delta_2x, delta_edge, delta_blossom).
        """
        delta_edge = -1
        delta_blossom: Optional[NonTrivialBlossom] = None

        # Compute delta1: minimum dual variable of any S-vertex.
        # All unmatched vertices have the same dual value, and this is
        # the minimum value among all S-vertices.
        delta_type = 1
        delta_2x = self.start_vertex_dual_2x - self.delta_sum_2x

        # Compute delta2: minimum slack of any edge between an S-vertex and
        # an unlabeled vertex.
        # This takes time O(log(n)).
        (e, slack) = self.delta2_get_min_edge()
        if (e != -1) and (slack <= delta_2x):
            delta_type = 2
            delta_2x = slack
            delta_edge = e

        # Compute delta3: half minimum slack of any edge between two top-level
        # S-blossoms.
        # This takes total time O(m * log(n)) per stage.
        (e, slack) = self.delta3_get_min_edge()
        if (e != -1) and (slack <= delta_2x):
            delta_type = 3
            delta_2x = slack
            delta_edge = e

        # Compute delta4: half minimum dual variable of a top-level T-blossom.
        # This takes time O(log(n)).
        if not self.delta4_queue.empty():
            blossom = self.delta4_queue.find_min().data
            assert blossom.label == LABEL_T
            assert blossom.parent is None
            blossom_dual = blossom.dual_var - self.delta_sum_2x
            if blossom_dual <= delta_2x:
                delta_type = 4
                delta_2x = blossom_dual
                delta_blossom = blossom

        return (delta_type, delta_2x, delta_edge, delta_blossom)

    #
    # Main algorithm:
    #

    def start(self) -> None:
        """Mark each vertex as the node of an alternating tree.

        Assign label S to all vertices and add them to the scan queue.

        This function takes time O(n + m).
        It is called once, at the beginning of the algorithm.
        """
        for x in range(self.graph.num_vertex):
            assert self.vertex_mate[x] == -1
            bx = self.top_level_blossom(x)
            assert bx.base_vertex == x

            # Assign label S.
            self.assign_blossom_label_s(bx)

            # Mark blossom as the root of an alternating tree.
            bx.tree_edge = None
            bx.tree_blossoms = {bx}

    def run_stage(self) -> bool:
        """Run one stage of the matching algorithm.

        The stage searches a maximum-weight augmenting path.
        If this path is found, it is used to augment the matching,
        thereby increasing the number of matched edges by 1.
        If no such path is found, the matching must already be optimal.

        This function takes time O((n + m) * log(n)).

        Returns:
            True if the matching was successfully augmented.
            False if no further improvement is possible.
        """

        # Each pass through the following loop is a "substage".
        # The substage tries to find an augmenting path.
        # If an augmenting path is found, we augment the matching and end
        # the stage. Otherwise we update the dual LPP problem and enter the
        # next substage, or stop if no further improvement is possible.
        #
        # This loop runs through at most O(n) iterations per stage.
        while True:

            # Consider the incident edges of newly labeled S-vertices.
            self.scan_new_s_vertices()

            # Calculate delta step in the dual LPP problem.
            (delta_type, delta_2x, delta_edge, delta_blossom
             ) = self.calc_dual_delta_step()

            # Update the running sum of delta steps.
            # This implicitly updates the dual variables as needed, because
            # the running delta sum is taken into account when calculating
            # dual values.
            self.delta_sum_2x += delta_2x

            if delta_type == 2:
                # Use the edge from S-vertex to unlabeled vertex that got
                # unlocked through the delta update.
                (x, y, _w) = self.graph.edges[delta_edge]
                if self.top_level_blossom(x).label != LABEL_S:
                    (x, y) = (y, x)
                self.extend_tree_s_to_t(x, y)

            elif delta_type == 3:
                # Use the S-to-S edge that got unlocked by the delta update.
                # This reveals either a new blossom or an augmenting path.
                (x, y, _w) = self.graph.edges[delta_edge]
                if self.add_s_to_s_edge(x, y):
                    # Matching was augmented. End the stage.
                    return True

            elif delta_type == 4:
                # Expand the T-blossom that reached dual value 0 through
                # the delta update.
                assert delta_blossom is not None
                self.expand_t_blossom(delta_blossom)

            else:
                # No further improvement possible. End the algorithm.
                assert delta_type == 1
                return False

    def cleanup(self) -> None:
        """Remove all alternating trees and mark all blossoms as unlabeled.

        Also applies delayed updates to dual variables.
        Also resets tracking of least-slack edges.

        This function takes time O((n + m) * log(n)).
        It is called once, at the end of the algorithm.
        """

        assert not self.scan_queue

        for blossom in itertools.chain(self.trivial_blossom,
                                       self.nontrivial_blossom):

            # Remove blossom label.
            if (blossom.parent is None) and (blossom.label != LABEL_NONE):
                self.reset_blossom_label(blossom)
            assert blossom.label == LABEL_NONE

            # Remove blossom from alternating tree.
            blossom.tree_edge = None
            blossom.tree_blossoms = None

            # Unwind lazy delta updates to vertex dual variables.
            if blossom.vertex_dual_offset != 0:
                for x in blossom.vertices():
                    self.vertex_dual_2x[x] += blossom.vertex_dual_offset
            blossom.vertex_dual_offset = 0

        assert self.delta2_queue.empty()
        assert self.delta3_queue.empty()
        assert self.delta4_queue.empty()


def _verify_blossom_edges(
        ctx: MatchingContext,
        blossom: NonTrivialBlossom,
        edge_slack_2x: list[float]
        ) -> None:
    """Descend down the blossom tree to find edges that are contained
    in blossoms.

    Adjust the slack of all contained edges to account for the dual variables
    of its containing blossoms.

    On the way down, keep track of the sum of dual variables of
    the containing blossoms.

    On the way up, keep track of the total number of matched edges
    in the subblossoms. Then check that all blossoms with non-zero
    dual variable are "full".

    Raises:
        MatchingError: If a blossom with non-zero dual is not full.
    """

    num_vertex = ctx.graph.num_vertex

    # For each vertex "x",
    # "vertex_depth[x]" is the depth of the smallest blossom on
    # the current descent path that contains "x".
    vertex_depth: list[int] = num_vertex * [0]

    # Keep track of the sum of blossom duals at each depth along
    # the current descent path.
    path_sum_dual: list[float] = [0]

    # Keep track of the number of matched edges at each depth along
    # the current descent path.
    path_num_matched: list[int] = [0]

    # Use an explicit stack to avoid deep recursion.
    stack: list[tuple[NonTrivialBlossom, int]] = [(blossom, -1)]

    while stack:
        (blossom, p) = stack[-1]
        depth = len(stack)

        if p == -1:
            # We just entered this sub-blossom.
            # Update the depth of all vertices in this sub-blossom.
            for x in blossom.vertices():
                vertex_depth[x] = depth

            # Calculate the sub of blossoms at the current depth.
            path_sum_dual.append(path_sum_dual[-1] + blossom.dual_var)

            # Initialize the number of matched edges at the current depth.
            path_num_matched.append(0)

            p += 1

        if p < len(blossom.subblossoms):
            # Update the sub-blossom pointer at the current level.
            stack[-1] = (blossom, p + 1)

            # Examine the next sub-blossom at the current level.
            sub = blossom.subblossoms[p]
            if isinstance(sub, NonTrivialBlossom):
                # Prepare to descent into the selected sub-blossom and
                # scan it recursively.
                stack.append((sub, -1))

            else:
                # Handle this trivial sub-blossom.
                # Scan its adjacent edges and find the smallest blossom
                # that contains each edge.
                for e in ctx.graph.adjacent_edges[sub.base_vertex]:
                    (x, y, _w) = ctx.graph.edges[e]

                    # Only process edges that are ordered out from this
                    # sub-blossom. This ensures that we process each edge in
                    # the blossom only once.
                    if x == sub.base_vertex:

                        edge_depth = vertex_depth[y]
                        if edge_depth > 0:
                            # This edge is contained in an ancestor blossom.
                            # Update its slack.
                            edge_slack_2x[e] += 2 * path_sum_dual[edge_depth]

                            # Update the number of matched edges in ancestor.
                            if ctx.vertex_mate[x] == y:
                                path_num_matched[edge_depth] += 1

        else:
            # We are now leaving the current sub-blossom.

            # Count the number of vertices inside this blossom.
            blossom_vertices = blossom.vertices()
            blossom_num_vertex = len(blossom_vertices)

            # Check that all blossoms are "full".
            # A blossom is full if all except one of its vertices are
            # matched to another vertex in the blossom.
            blossom_num_matched = path_num_matched[depth]
            if blossom_num_vertex != 2 * blossom_num_matched + 1:
                raise MatchingError(
                    "Verification failed: blossom non-full"
                    f" dual={blossom.dual_var}"
                    f" nvertex={blossom_num_vertex}"
                    f" nmatched={blossom_num_matched}")

            # Update the number of matched edges in the parent blossom to
            # take into account the matched edges in this blossom.
            path_num_matched[depth - 1] += path_num_matched[depth]

            # Revert the depth of the vertices in this sub-blossom.
            for x in blossom_vertices:
                vertex_depth[x] = depth - 1

            # Trim the descending path.
            path_sum_dual.pop()
            path_num_matched.pop()

            # Remove the current blossom from the stack.
            # We thus continue our scan of the parent blossom.
            stack.pop()


def verify_optimum(ctx: MatchingContext) -> None:
    """Verify that the optimum solution has been found.

    This function takes time O(n**2).

    Raises:
        MatchingError: If the solution is not optimal.
    """

    num_vertex = ctx.graph.num_vertex
    num_edge = len(ctx.graph.edges)

    # Check that each matched edge actually exists in the graph.
    num_matched_vertex = 0
    for x in range(num_vertex):
        y = ctx.vertex_mate[x]
        if y != -1:
            if ctx.vertex_mate[y] != x:
                raise MatchingError(
                    "Verification failed:"
                    f" asymmetric match of vertex {x} and {y}")
            num_matched_vertex += 1

    num_matched_edge = 0
    for (x, y, _w) in ctx.graph.edges:
        if ctx.vertex_mate[x] == y:
            num_matched_edge += 1

    if num_matched_vertex != 2 * num_matched_edge:
        raise MatchingError(
            f"Verification failed: {num_matched_vertex} matched vertices"
            f" inconsistent with {num_matched_edge} matched edges")

    # Check that all dual variables are non-negative.
    for x in range(num_vertex):
        if ctx.vertex_dual_2x[x] < 0:
            raise MatchingError(
                "Verification failed:"
                f" vertex {x} has negative dual {ctx.vertex_dual_2x[x]/2}")

    for blossom in ctx.nontrivial_blossom:
        if blossom.dual_var < 0:
            raise MatchingError("Verification failed:"
                                f" negative blossom dual {blossom.dual_var}")

    # Check that all unmatched vertices have zero dual.
    for x in range(num_vertex):
        if ctx.vertex_mate[x] == -1 and ctx.vertex_dual_2x[x] != 0:
            raise MatchingError(
                f"Verification failed: Unmatched vertex {x}"
                f" has non-zero dual {ctx.vertex_dual_2x[x]/2}")

    # Calculate the slack of each edge.
    # A correction will be needed for edges inside blossoms.
    edge_slack_2x: list[float] = [
        ctx.vertex_dual_2x[x] + ctx.vertex_dual_2x[y] - 2 * w
        for (x, y, w) in ctx.graph.edges]

    # Descend down each top-level blossom.
    # Adjust edge slacks to account for the duals of its containing blossoms.
    # And check that all blossoms are full.
    # This takes total time O(n**2).
    for blossom in ctx.nontrivial_blossom:
        if blossom.parent is None:
            _verify_blossom_edges(ctx, blossom, edge_slack_2x)

    # We now know the correct slack of each edge.
    # Check that all edges have non-negative slack.
    min_edge_slack = min(edge_slack_2x)
    if min_edge_slack < 0:
        raise MatchingError(
            f"Verification failed: negative edge slack {min_edge_slack/2}")

    # Check that all matched edges have zero slack.
    for e in range(num_edge):
        (x, y, _w) = ctx.graph.edges[e]
        if ctx.vertex_mate[x] == y and edge_slack_2x[e] != 0:
            raise MatchingError(
                "Verification failed:"
                f" matched edge ({x}, {y}) has slack {edge_slack_2x[e]/2}")

    # Optimum solution confirmed.