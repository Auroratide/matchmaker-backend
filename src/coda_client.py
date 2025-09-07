import json
import os
import threading
from typing import Iterable, List, Set, Tuple


def _normalize_pair(a: str, b: str) -> Tuple[str, str]:
	"""Return a stable, order-independent pair key."""
	return tuple(sorted((a, b)))  # type: ignore[return-value]


class PairStore:
	"""A simple JSON-backed placeholder store for matched pairs.

	Structure on disk is a JSON array of 2-item arrays, e.g.:
	[
		["alice", "bob"],
		["charlie", "dana"]
	]

	This is a placeholder that can be swapped for a real Coda client later.
	"""

	def __init__(self, file_path: str | None = None) -> None:
		root_dir = os.path.dirname(os.path.dirname(__file__))  # project root
		default_path = os.path.join(root_dir, "pairs.json")
		self.file_path = file_path or os.environ.get("PAIR_STORE_PATH", default_path)
		self._lock = threading.Lock()

	def _read_pairs(self) -> Set[Tuple[str, str]]:
		if not os.path.exists(self.file_path):
			return set()
		with open(self.file_path, "r", encoding="utf-8") as f:
			try:
				data = json.load(f)
			except json.JSONDecodeError:
				return set()
		result: Set[Tuple[str, str]] = set()
		if isinstance(data, list):
			for item in data:
				if isinstance(item, list) and len(item) == 2 and all(isinstance(x, str) for x in item):
					result.add(_normalize_pair(item[0], item[1]))
		return result

	def _write_pairs(self, pairs: Set[Tuple[str, str]]) -> None:
		dirname = os.path.dirname(self.file_path)
		if dirname and not os.path.exists(dirname):
			os.makedirs(dirname, exist_ok=True)
		serializable: List[List[str]] = [[a, b] for (a, b) in sorted(pairs)]
		with open(self.file_path, "w", encoding="utf-8") as f:
			json.dump(serializable, f, indent=2, ensure_ascii=False)

	def load_pairs(self) -> Set[Tuple[str, str]]:
		"""Load all existing pairs as normalized tuples."""
		with self._lock:
			return self._read_pairs()

	def has_pair(self, a: str, b: str) -> bool:
		"""Check if a pair exists (order-insensitive)."""
		key = _normalize_pair(a, b)
		with self._lock:
			return key in self._read_pairs()

	def add_pairs(self, pairs: Iterable[Tuple[str, str]]) -> int:
		"""Add pairs to the store. Returns number of newly added pairs."""
		with self._lock:
			existing = self._read_pairs()
			before = len(existing)
			for a, b in pairs:
				existing.add(_normalize_pair(a, b))
			self._write_pairs(existing)
			return len(existing) - before


