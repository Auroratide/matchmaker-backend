from src.coda_client import PairStore


class _Vec:
	def __init__(self, vid: str, past: list[str]):
		self.id = vid
		self.metadata = {"pastPairings": past}


def test_load_pairs_builds_normalized_set(monkeypatch):
	# Ensure envs exist to construct PairStore without hitting network
	monkeypatch.setenv("CODA_API_TOKEN", "x")
	monkeypatch.setenv("CODA_DOC_ID", "x")
	monkeypatch.setenv("CODA_PAIRINGS_TABLE_ID", "x")
	monkeypatch.setenv("CODA_PERSON_1_ID_COL_ID", "c-p1id")
	monkeypatch.setenv("CODA_PERSON_2_ID_COL_ID", "c-p2id")
	monkeypatch.setenv("CODA_SEND_EMAIL_COL_ID", "c-send")

	store = PairStore()
	vectors = [
		_Vec("alice", ["bob", "charlie"]),
		_Vec("bob", ["alice"]),
		_Vec("dana", []),
	]
	result = store.load_pairs(vectors)
	assert ("alice", "bob") in result
	assert ("alice", "charlie") in result
	# Dana has no past pairings
	assert not any("dana" in p for p in result)
