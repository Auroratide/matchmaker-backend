from src.coda_client import CodaClient


def test_coda_add_pairs_sorts_and_sends_rows(monkeypatch):
	# Ensure envs exist to construct CodaClient without hitting network
	monkeypatch.setenv("CODA_API_TOKEN", "x")
	monkeypatch.setenv("CODA_DOC_ID", "doc")
	monkeypatch.setenv("CODA_PAIRINGS_TABLE_ID", "tbl")
	monkeypatch.setenv("CODA_PERSON_1_ID_COL_ID", "c-p1id")
	monkeypatch.setenv("CODA_PERSON_2_ID_COL_ID", "c-p2id")
	monkeypatch.setenv("CODA_SEND_EMAIL_COL_ID", "c-send")

	# Capture outgoing request
	class _Resp:
		def __init__(self, code=202, text="accepted"):
			self.status_code = code
			self.text = text

	captured = {}
	def fake_post(url, headers=None, json=None, timeout=None):
		captured["url"] = url
		captured["headers"] = headers
		captured["json"] = json
		captured["timeout"] = timeout
		return _Resp()

	monkeypatch.setattr("requests.post", fake_post)

	coda = CodaClient()
	count = coda.add_pairs([("b", "a")])
	assert count == 1

	payload = captured["json"]
	assert payload["keyColumns"] == ["c-p1id", "c-p2id"]
	assert len(payload["rows"]) == 1
	cells = payload["rows"][0]["cells"]
	# Expect sorted order (a, b)
	assert cells[0] == {"column": "c-p1id", "value": "a"}
	assert cells[1] == {"column": "c-p2id", "value": "b"}
	assert cells[2] == {"column": "c-send", "value": True}