import os
import tempfile
from src.coda_client import PairStore


def test_pairstore_normalizes_and_persists():
	with tempfile.TemporaryDirectory() as tmpdir:
		path = os.path.join(tmpdir, "pairs.json")
		store = PairStore(file_path=path)

		# initially empty
		assert store.load_pairs() == set()

		added = store.add_pairs([("b", "a"), ("a", "b"), ("c", "d")])
		assert added == 2  # only two unique pairs

		pairs = store.load_pairs()
		assert ("a", "b") in pairs or ("b", "a") in pairs
		assert ("c", "d") in pairs or ("d", "c") in pairs

		# idempotent add
		added2 = store.add_pairs([("a", "b")])
		assert added2 == 0


