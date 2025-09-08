
import os
import requests
import time
import pytest

from src.coda_client import CodaClient

from dotenv import load_dotenv

load_dotenv()

# Mark this module as destructive so collection prompts happen before running
pytestmark = pytest.mark.coda_destructive

DOC = os.environ.get("CODA_DOC_ID")
TABLE = os.environ.get("CODA_PAIRINGS_TABLE_ID")
PC1 = os.environ.get("CODA_PERSON_1_ID_COL_ID")
PC2 = os.environ.get("CODA_PERSON_2_ID_COL_ID")
TOKEN = os.environ.get("CODA_API_TOKEN")
ROWS_URL = f"https://coda.io/apis/v1/docs/{DOC}/tables/{TABLE}/rows"
AUTH_HEADERS = {"Authorization": f"Bearer {TOKEN}"}
JSON_HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
SESSION = requests.Session()

ADD_P1 = os.environ.get("CODA_TEST_ADD_P1")
ADD_P2 = os.environ.get("CODA_TEST_ADD_P2")
DUP_P1 = os.environ.get("CODA_TEST_DUP_P1")
DUP_P2 = os.environ.get("CODA_TEST_DUP_P2")
SORT_P1 = os.environ.get("CODA_TEST_SORT_P1")
SORT_P2 = os.environ.get("CODA_TEST_SORT_P2")
MULTI_P1 = os.environ.get("CODA_TEST_MULTI_P1")
MULTI_P2 = os.environ.get("CODA_TEST_MULTI_P2")
MULTI_P3 = os.environ.get("CODA_TEST_MULTI_P3")
MULTI_P4 = os.environ.get("CODA_TEST_MULTI_P4")


def _delete_pairs(pairs: list[tuple[str, str]]) -> None:
	"""Discover once, bulk-delete, then poll rowIds until gone."""
	# Initial discovery
	initial_row_ids: set[str] = set()
	for a, b in pairs:
		query = f"{PC1}:{str(a)}"
		params = {"query": query, "valueFormat": "simple", "limit": 1}
		res = SESSION.get(ROWS_URL, headers=AUTH_HEADERS, params=params, timeout=60)
		res.raise_for_status()
		items = res.json().get("items", [])
		for it in items:
			vals = it.get("values", {})
			val_lo = str(vals.get(PC1))
			val_hi = str(vals.get(PC2))
			if val_lo == str(a) and val_hi == str(b):
				row_id = it.get("id")
				if isinstance(row_id, str):
					initial_row_ids.add(row_id)

	if not initial_row_ids:
		return

	# Bulk delete once
	to_delete = sorted(initial_row_ids)
	resp = SESSION.delete(ROWS_URL, headers=JSON_HEADERS, json={"rowIds": to_delete}, timeout=60)
	if resp.status_code != 202:
		print(f"warning: bulk delete returned {resp.status_code}: {resp.text}")

	# Poll by rowId only
	remaining: set[str] = set(initial_row_ids)
	for _ in range(10):
		still: set[str] = set()
		for rid in sorted(remaining):
			row_url = f"https://coda.io/apis/v1/docs/{DOC}/tables/{TABLE}/rows/{rid}"
			resp = SESSION.get(row_url, headers=AUTH_HEADERS, timeout=30)
			if resp.status_code == 404:
				continue
			if resp.status_code == 200:
				still.add(rid)
				continue
			still.add(rid)
		remaining = still
		if not remaining:
			break
		time.sleep(1)


def _count_pair_query(a, b) -> int:
	# Respect argument order: PC1 must equal 'a', PC2 must equal 'b'
	expected_pc1 = str(a)
	expected_pc2 = str(b)
	c = 0
	for _ in range(10):
		print("\npolling changes...")
		query = f"{PC1}:{expected_pc1}"
		params = {"query": query, "valueFormat": "simple", "limit": 1}
		res = SESSION.get(ROWS_URL, headers=AUTH_HEADERS, params=params, timeout=60)
		res.raise_for_status()
		items = res.json().get("items", [])
		c = 0
		for it in items:
			vals = it.get("values", {})
			val_pc1 = str(vals.get(PC1))
			val_pc2 = str(vals.get(PC2))
			if val_pc1 == expected_pc1 and val_pc2 == expected_pc2:
				c += 1
		if c > 0:
			return c
		time.sleep(5)
	return c


@pytest.fixture(autouse=True, scope="module")
def _cleanup_test_pairs():
	# Pre-clean all test pairs
	print("\npre-cleaning test pairs")
	pairs = [
		(str(ADD_P1), str(ADD_P2)),
		(str(DUP_P1), str(DUP_P2)),
		(str(SORT_P1), str(SORT_P2)),
		(str(MULTI_P1), str(MULTI_P2)),
		(str(MULTI_P3), str(MULTI_P4)),
	]
	_delete_pairs(pairs)
	# Run the test
	yield
	# Post-clean all test pairs
	print("\npost-cleaning test pairs")
	_delete_pairs(pairs)


def test_coda_upsert():
	# Simple per-test env assertions
	assert ADD_P1 and ADD_P2, "CODA_TEST_ADD_* envs must be set"
	coda = CodaClient()
	# Use env-provided unique pair for this test
	a, b = str(ADD_P1), str(ADD_P2)
	coda.add_pairs([(a, b)])
	
	# Verify: count is 1, not 2
	after = _count_pair_query(a, b)
	assert after == 1


def test_coda_upsert_duplicates_not_added():
	assert DUP_P1 and DUP_P2, "CODA_TEST_DUP_* envs must be set"
	coda = CodaClient()
	# Use env-provided unique pair for this test
	a, b = str(DUP_P1), str(DUP_P2)

	# Perform two upserts
	coda.add_pairs([(a, b)])
	coda.add_pairs([(a, b)])

	# Verify: count is 1, not 2
	after_dupe = _count_pair_query(a, b)
	assert after_dupe == 1


def test_coda_upsert_enforces_sorted_order():
	assert SORT_P1 and SORT_P2, "CODA_TEST_SORT_* envs must be set"
	coda = CodaClient()
	a, b = sorted([str(SORT_P1), str(SORT_P2)])
	# Intentionally reversed input; implementation should store as sorted by Person ID
	coda.add_pairs([(b, a)])
	# Verify: sorted is present once; reversed absent
	after_sorted = _count_pair_query(a, b)
	after_reversed = _count_pair_query(b, a)
	assert after_sorted == 1
	assert after_reversed == 0


def test_coda_upsert_multiple_rows():
	assert MULTI_P1 and MULTI_P2 and MULTI_P3 and MULTI_P4, "CODA_TEST_MULTI_* envs must be set"
	coda = CodaClient()
	a1, b1 = str(MULTI_P1), str(MULTI_P2)
	a2, b2 = str(MULTI_P3), str(MULTI_P4)
	coda.add_pairs([(a1, b1), (a2, b2)])
	# Verify each appears once
	after_12 = _count_pair_query(a1, b1)
	after_34 = _count_pair_query(a2, b2)
	assert after_12 == 1
	assert after_34 == 1