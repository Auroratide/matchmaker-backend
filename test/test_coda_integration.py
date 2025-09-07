import os
import pytest

from src.coda_client import PairStore


required_envs = [
	"CODA_API_TOKEN",
	"CODA_DOC_ID",
	"CODA_PAIRINGS_TABLE_ID",
	"CODA_PERSON_1_COL_ID",
	"CODA_PERSON_2_COL_ID",
	"CODA_PERSON_1_ID_COL_ID",
	"CODA_PERSON_2_ID_COL_ID",
	"CODA_SEND_EMAIL_COL_ID",
	"CODA_TEST_PERSON1_ID",
	"CODA_TEST_PERSON2_ID",
]


skip_reason = "Missing one or more required env vars for Coda integration test"
skip_integration = any(os.environ.get(k) in (None, "") for k in required_envs)


@pytest.mark.skipif(skip_integration, reason=skip_reason)
def test_coda_upsert_smoke():
	"""Smoke test: upsert one pairing row to Coda.

	Requires CODA_* env vars and CODA_TEST_PERSON{1,2}_ID to be set.
	"""
	store = PairStore()
	p1 = os.environ["CODA_TEST_PERSON1_ID"]
	p2 = os.environ["CODA_TEST_PERSON2_ID"]
	rows = store.add_pairs([(p1, p2)])
	assert rows >= 1


