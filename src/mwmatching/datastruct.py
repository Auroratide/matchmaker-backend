"""Data structures for matching."""

from __future__ import annotations

from typing import Generic, Optional, TypeVar


_NameT = TypeVar("_NameT")
_NameT2 = TypeVar("_NameT2")
_ElemT = TypeVar("_ElemT")
_ElemT2 = TypeVar("_ElemT2")


class ConcatenableQueue(Generic[_NameT, _ElemT]):
    """Priority queue supporting efficient merge and split operations.

    This is a combination of a disjoint set and a priority queue.
    A queue has a "name", which can be any Python object.
    Each element has associated "data", which can be any Python object.
    Each element has a priority.

    The following operations can be done efficiently:
     - Create a new queue containing one new element.
     - Find the name of the queue that contains a given element.
     - Change the priority of a given element.
     - Find the element with lowest priority in a given queue.
     - Merge two or more queues.
     - Undo a previous merge step.

    This data structure is implemented as a 2-3 tree with minimum-priority
    tracking added to it.
    """

    __slots__ = ("name", "tree", "first_node", "sub_queues")

    class BaseNode(Generic[_NameT2, _ElemT2]):
        """Node in the 2-3 tree."""

        __slots__ = ("owner", "min_node", "height", "parent", "childs")

        def __init__(self,
                     min_node: ConcatenableQueue.Node[_NameT2, _ElemT2],
                     height: int
                     ) -> None:
            """Initialize a new node."""
            self.owner: Optional[ConcatenableQueue[_NameT2, _ElemT2]] = None
            self.min_node = min_node
            self.height = height
            self.parent: Optional[ConcatenableQueue.BaseNode[_NameT2,
                                                             _ElemT2]]
            self.parent = None
            self.childs: list[ConcatenableQueue.BaseNode[_NameT2, _ElemT2]]
            self.childs = []

    class Node(BaseNode[_NameT2, _ElemT2]):
        """Leaf node in the 2-3 tree, representing an element in the queue."""

        __slots__ = ("data", "prio")

        def __init__(self, data: _ElemT2, prio: float) -> None:
            """Initialize a new leaf node.

            This method should not be called directly.
            Instead, call ConcatenableQueue.insert().
            """
            super().__init__(min_node=self, height=0)
            self.data = data
            self.prio = prio

        def find(self) -> _NameT2:
            """Return the name of the queue that contains this element.

            This function takes time O(log(n)).
            """
            node: ConcatenableQueue.BaseNode[_NameT2, _ElemT2] = self
            while node.parent is not None:
                node = node.parent
            assert node.owner is not None
            return node.owner.name

        def set_prio(self, prio: float) -> None:
            """Change the priority of this element.

            This function takes time O(log(n)).
            """
            self.prio = prio
            node = self.parent
            while node is not None:
                min_node = node.childs[0].min_node
                for child in node.childs[1:]:
                    if child.min_node.prio < min_node.prio:
                        min_node = child.min_node
                node.min_node = min_node
                node = node.parent

    def __init__(self, name: _NameT) -> None:
        """Initialize an empty queue.

        This function takes time O(1).

        Parameters:
            name: Name to assign to the new queue.
        """
        self.name = name
        self.tree: Optional[ConcatenableQueue.BaseNode[_NameT, _ElemT]] = None
        self.first_node: Optional[ConcatenableQueue.Node[_NameT, _ElemT]]
        self.first_node = None
        self.sub_queues: list[ConcatenableQueue[_NameT, _ElemT]] = []

    def clear(self) -> None:
        """Remove all elements from the queue.

        This function takes time O(n).
        """
        node = self.tree
        self.tree = None
        self.first_node = None
        self.sub_queues = []

        # Wipe pointers to enable refcounted garbage collection.
        if node is not None:
            node.owner = None
        while node is not None:
            node.min_node = None  # type: ignore
            prev_node = node
            if node.childs:
                node = node.childs.pop()
            else:
                node = node.parent
                prev_node.parent = None

    def insert(self, elem: _ElemT, prio: float) -> Node[_NameT, _ElemT]:
        """Insert an element into the empty queue.

        This function can only be used if the queue is empty.
        Non-empty queues can grow only by merging.

        This function takes time O(1).

        Parameters:
            elem: Element to insert.
            prio: Initial priority of the new element.
        """
        assert self.tree is None
        self.tree = ConcatenableQueue.Node(elem, prio)
        self.tree.owner = self
        self.first_node = self.tree
        return self.tree

    def min_prio(self) -> float:
        """Return the minimum priority of any element in the queue.

        The queue must be non-empty.
        This function takes time O(1).
        """
        node = self.tree
        assert node is not None
        return node.min_node.prio

    def min_elem(self) -> _ElemT:
        """Return the element with minimum priority.

        The queue must be non-empty.
        This function takes time O(1).
        """
        node = self.tree
        assert node is not None
        return node.min_node.data

    def merge(self,
              sub_queues: list[ConcatenableQueue[_NameT, _ElemT]]
              ) -> None:
        """Merge the specified queues.

        This queue must inititially be empty.
        All specified sub-queues must initially be non-empty.

        This function removes all elements from the specified sub-queues
        and adds them to this queue.

        After merging, this queue retains a reference to the list of
        sub-queues.

        This function takes time O(len(sub_queues) * log(n)).
        """
        assert self.tree is None
        assert not self.sub_queues
        assert sub_queues

        # Keep the list of sub-queues.
        self.sub_queues = sub_queues

        # Move the root node from the first sub-queue to this queue.
        # Clear its owner pointer.
        self.tree = sub_queues[0].tree
        self.first_node = sub_queues[0].first_node
        assert self.tree is not None
        sub_queues[0].tree = None
        self.tree.owner = None

        # Merge remaining sub-queues.
        for sub in sub_queues[1:]:

            # Pull the root node from the sub-queue.
            # Clear its owner pointer.
            subtree = sub.tree
            assert subtree is not None
            assert subtree.owner is sub
            subtree.owner = None

            # Merge our current tree with the tree from the sub-queue.
            self.tree = self._join(self.tree, subtree)

        # Put the owner pointer in the root node.
        self.tree.owner = self

    def split(self) -> None:
        """Undo the merge step that filled this queue.

        Remove all elements from this queue and put them back in
        the sub-queues from which they came.

        After splitting, this queue will be empty.

        This function takes time O(k * log(n)).
        """
        assert self.tree is not None
        assert self.sub_queues

        # Clear the owner pointer from the root node.
        assert self.tree.owner is self
        self.tree.owner = None

        # Split the tree to reconstruct each sub-queue.
        for sub in self.sub_queues[:0:-1]:

            assert sub.first_node is not None
            (tree, rtree) = self._split_tree(sub.first_node)

            # Assign the right tree to the sub-queue.
            sub.tree = rtree
            rtree.owner = sub

        # Put the remaining tree in the first sub-queue.
        self.sub_queues[0].tree = tree
        tree.owner = self.sub_queues[0]

        # Make this queue empty.
        self.tree = None
        self.first_node = None
        self.sub_queues = []

    @staticmethod
    def _repair_node(node: BaseNode[_NameT, _ElemT]) -> None:
        """Repair min_prio attribute of an internal node."""
        min_node = node.childs[0].min_node
        for child in node.childs[1:]:
            if child.min_node.prio < min_node.prio:
                min_node = child.min_node
        node.min_node = min_node

    @staticmethod
    def _new_internal_node(ltree: BaseNode[_NameT, _ElemT],
                           rtree: BaseNode[_NameT, _ElemT]
                           ) -> BaseNode[_NameT, _ElemT]:
        """Create a new internal node with 2 child nodes."""
        assert ltree.height == rtree.height
        height = ltree.height + 1
        if ltree.min_node.prio <= rtree.min_node.prio:
            min_node = ltree.min_node
        else:
            min_node = rtree.min_node
        node = ConcatenableQueue.BaseNode(min_node, height)
        node.childs = [ltree, rtree]
        ltree.parent = node
        rtree.parent = node
        return node

    def _join_right(self,
                    ltree: BaseNode[_NameT, _ElemT],
                    rtree: BaseNode[_NameT, _ElemT]
                    ) -> BaseNode[_NameT, _ElemT]:
        """Join two trees together.

        The initial left subtree must be higher than the right subtree.

        Return the root node of the joined tree.
        """

        # Descend down the right spine of the left tree until we
        # reach a node just above the right tree.
        node = ltree
        while node.height > rtree.height + 1:
            node = node.childs[-1]

        assert node.height == rtree.height + 1

        # Find a node in the left tree to insert the right tree as child.
        while len(node.childs) == 3:
            # This node already has 3 childs so we can not add the right tree.
            # Rearrange into 2 nodes with 2 childs each, then solve it
            # at the parent level.
            #
            #       N                     N       R'
            #     / | \                  / \     / \
            #    /  |  \        --->    /   \   /   \
            #   A   B   C   R           A   B   C   R
            #
            child = node.childs.pop()
            self._repair_node(node)
            rtree = self._new_internal_node(child, rtree)
            if node.parent is None:
                # Create a new root node.
                return self._new_internal_node(node, rtree)
            node = node.parent

        # Insert the right tree as child of this node.
        assert len(node.childs) < 3
        node.childs.append(rtree)
        rtree.parent = node

        # Repair min-prio pointers of ancestors.
        while True:
            self._repair_node(node)
            if node.parent is None:
                break
            node = node.parent

        return node

    def _join_left(self,
                   ltree: BaseNode[_NameT, _ElemT],
                   rtree: BaseNode[_NameT, _ElemT]
                   ) -> BaseNode[_NameT, _ElemT]:
        """Join two trees together.

        The initial left subtree must be lower than the right subtree.

        Return the root node of the joined tree.
        """

        # Descend down the left spine of the right tree until we
        # reach a node just above the left tree.
        node = rtree
        while node.height > ltree.height + 1:
            node = node.childs[0]

        assert node.height == ltree.height + 1

        # Find a node in the right tree to insert the left tree as child.
        while len(node.childs) == 3:
            # This node already has 3 childs so we can not add the left tree.
            # Rearrange into 2 nodes with 2 childs each, then solve it
            # at the parent level.
            #
            #          N                L'      N
            #        / | \             / \     / \
            #       /  |  \    --->   /   \   /   \
            #  L   A   B   C          L   A   B   C
            #
            child = node.childs.pop(0)
            self._repair_node(node)
            ltree = self._new_internal_node(ltree, child)
            if node.parent is None:
                # Create a new root node.
                return self._new_internal_node(ltree, node)
            node = node.parent

        # Insert the left tree as child of this node.
        assert len(node.childs) < 3
        node.childs.insert(0, ltree)
        ltree.parent = node

        # Repair min-prio pointers of ancestors.
        while True:
            self._repair_node(node)
            if node.parent is None:
                break
            node = node.parent

        return node

    def _join(self,
              ltree: BaseNode[_NameT, _ElemT],
              rtree: BaseNode[_NameT, _ElemT]
              ) -> BaseNode[_NameT, _ElemT]:
        """Join two trees together.

        The left and right subtree must be consistent 2-3 trees.
        Initial parent pointers of these subtrees are ignored.

        Return the root node of the joined tree.
        """
        if ltree.height > rtree.height:
            return self._join_right(ltree, rtree)
        elif ltree.height < rtree.height:
            return self._join_left(ltree, rtree)
        else:
            return self._new_internal_node(ltree, rtree)

    def _split_tree(self,
                    split_node: BaseNode[_NameT, _ElemT]
                    ) -> tuple[BaseNode[_NameT, _ElemT],
                               BaseNode[_NameT, _ElemT]]:
        """Split a tree on a specified node.

        Two new trees will be constructed.
        Leaf nodes to the left of "split_node" will go to the left tree.
        Leaf nodes to the right of "split_node", and "split_node" itself,
        will go to the right tree.

        Return tuple (ltree, rtree).
        """

        # Detach "split_node" from its parent.
        # Assign it to the right tree.
        parent = split_node.parent
        split_node.parent = None

        # The left tree is initially empty.
        # The right tree initially contains only "split_node".
        ltree: Optional[ConcatenableQueue.BaseNode[_NameT, _ElemT]] = None
        rtree = split_node

        # Walk up to the root of the tree.
        # On the way up, detach each node from its parent and join its
        # child nodes to the appropriate tree.
        node = split_node
        while parent is not None:

            # Ascend to the parent node.
            child = node
            node = parent
            parent = node.parent

            # Detach "node" from its parent.
            node.parent = None

            if len(node.childs) == 3:
                if node.childs[0] is child:
                    # "node" has 3 child nodes.
                    # Its left subtree has already been split.
                    # Turn it into a 2-node and join it to the right tree.
                    node.childs.pop(0)
                    self._repair_node(node)
                    rtree = self._join(rtree, node)
                elif node.childs[2] is child:
                    # "node" has 3 child nodes.
                    # Its right subtree has already been split.
                    # Turn it into a 2-node and join it to the left tree.
                    node.childs.pop()
                    self._repair_node(node)
                    if ltree is None:
                        ltree = node
                    else:
                        ltree = self._join(node, ltree)
                else:
                    # "node has 3 child nodes.
                    # Its middle subtree has already been split.
                    # Join its left child to the left tree, and its right
                    # child to the right tree, then delete "node".
                    node.childs[0].parent = None
                    node.childs[2].parent = None
                    if ltree is None:
                        ltree = node.childs[0]
                    else:
                        ltree = self._join(node.childs[0], ltree)
                    rtree = self._join(rtree, node.childs[2])

            elif node.childs[0] is child:
                # "node" has 2 child nodes.
                # Its left subtree has already been split.
                # Join its right child to the right tree, then delete "node".
                node.childs[1].parent = None
                rtree = self._join(rtree, node.childs[1])

            else:
                # "node" has 2 child nodes.
                # Its right subtree has already been split.
                # Join its left child to the left tree, then delete "node".
                node.childs[0].parent = None
                if ltree is None:
                    ltree = node.childs[0]
                else:
                    ltree = self._join(node.childs[0], ltree)

        assert ltree is not None
        return (ltree, rtree)


class PriorityQueue(Generic[_ElemT]):
    """Priority queue based on a binary heap."""

    __slots__ = ("heap", )

    class Node(Generic[_ElemT2]):
        """Node in the priority queue."""

        __slots__ = ("index", "prio", "data")

        def __init__(
                self,
                index: int,
                prio: float,
                data: _ElemT2
                ) -> None:
            self.index = index
            self.prio = prio
            self.data = data

    def __init__(self) -> None:
        """Initialize an empty queue."""
        self.heap: list[PriorityQueue.Node[_ElemT]] = []

    def clear(self) -> None:
        """Remove all elements from the queue.

        This function takes time O(n).
        """
        self.heap.clear()

    def empty(self) -> bool:
        """Return True if the queue is empty."""
        return (not self.heap)

    def find_min(self) -> Node[_ElemT]:
        """Return the minimum-priority node.

        This function takes time O(1).
        """
        if not self.heap:
            raise IndexError("Queue is empty")
        return self.heap[0]

    def _sift_up(self, index: int) -> None:
        """Repair the heap along an ascending path to the root."""
        node = self.heap[index]
        prio = node.prio

        pos = index
        while pos > 0:
            tpos = (pos - 1) // 2
            tnode = self.heap[tpos]
            if tnode.prio <= prio:
                break
            tnode.index = pos
            self.heap[pos] = tnode
            pos = tpos

        if pos != index:
            node.index = pos
            self.heap[pos] = node

    def _sift_down(self, index: int) -> None:
        """Repair the heap along a descending path."""
        num_elem = len(self.heap)
        node = self.heap[index]
        prio = node.prio

        pos = index
        while True:
            tpos = 2 * pos + 1
            if tpos >= num_elem:
                break
            tnode = self.heap[tpos]

            qpos = tpos + 1
            if qpos < num_elem:
                qnode = self.heap[qpos]
                if qnode.prio <= tnode.prio:
                    tpos = qpos
                    tnode = qnode

            if tnode.prio >= prio:
                break

            tnode.index = pos
            self.heap[pos] = tnode
            pos = tpos

        if pos != index:
            node.index = pos
            self.heap[pos] = node

    def insert(self, prio: float, data: _ElemT) -> Node:
        """Insert a new element into the queue.

        This function takes time O(log(n)).

        Returns:
            Node that represents the new element.
        """
        new_index = len(self.heap)
        node = self.Node(new_index, prio, data)
        self.heap.append(node)
        self._sift_up(new_index)
        return node

    def delete(self, elem: Node[_ElemT]) -> None:
        """Delete the specified element from the queue.

        This function takes time O(log(n)).
        """
        index = elem.index
        assert self.heap[index] is elem

        node = self.heap.pop()
        if index < len(self.heap):
            node.index = index
            self.heap[index] = node
            if node.prio < elem.prio:
                self._sift_up(index)
            elif node.prio > elem.prio:
                self._sift_down(index)

    def decrease_prio(self, elem: Node[_ElemT], prio: float) -> None:
        """Decrease the priority of an existing element in the queue.

        This function takes time O(log(n)).
        """
        assert self.heap[elem.index] is elem
        assert prio <= elem.prio
        elem.prio = prio
        self._sift_up(elem.index)

    def increase_prio(self, elem: Node[_ElemT], prio: float) -> None:
        """Increase the priority of an existing element in the queue.

        This function takes time O(log(n)).
        """
        assert self.heap[elem.index] is elem
        assert prio >= elem.prio
        elem.prio = prio
        self._sift_down(elem.index)