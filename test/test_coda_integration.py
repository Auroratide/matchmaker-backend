import os
import requests
import time
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


def _extract_row_id(cell_value):
	if isinstance(cell_value, dict):
		return cell_value.get("rowId") or cell_value.get("url") or str(cell_value)
	if isinstance(cell_value, list) and cell_value:
		v = cell_value[0]
		return v.get("rowId") if isinstance(v, dict) else str(v)
	return str(cell_value)


def _cleanup_pair(p1: str, p2: str) -> None:
	"""Delete any existing rows that reference this pair in either order."""
	headers = {
		"Authorization": f"Bearer {os.environ['CODA_API_TOKEN']}",
		"Content-Type": "application/json",
	}
	url = f"https://coda.io/apis/v1/docs/{os.environ['CODA_DOC_ID']}/tables/{os.environ['CODA_PAIRINGS_TABLE_ID']}/rows"
	pc1 = os.environ["CODA_PERSON_1_COL_ID"]
	pc2 = os.environ["CODA_PERSON_2_COL_ID"]
	res = requests.get(url, headers=headers, params={"valueFormat": "rich", "limit": 500})
	res.raise_for_status()
	items = res.json().get("items", [])
	to_delete = []
	for it in items:
		vals = it.get("values", {})
		v1 = _extract_row_id(vals.get(pc1))
		v2 = _extract_row_id(vals.get(pc2))
		if {v1, v2} == {p1, p2}:
			row_id = it.get("id")
			if isinstance(row_id, str):
				to_delete.append(row_id)
	if to_delete:
		requests.delete(url, headers=headers, json={"rowIds": to_delete})


@pytest.mark.skipif(skip_integration, reason=skip_reason)
def test_coda_upsert_duplicates_not_added():
	store = PairStore()
	p1 = os.environ["CODA_TEST_PERSON1_ID"]
	p2 = os.environ["CODA_TEST_PERSON2_ID"]
	_cleanup_pair(p1, p2)
	# First upsert
	store.add_pairs([(p1, p2)])
	# Duplicate, reversed order
	store.add_pairs([(p2, p1)])

	# Fetch rows in rich format and ensure exactly one row matches the pair
	headers = {"Authorization": f"Bearer {os.environ['CODA_API_TOKEN']}"}
	url = f"https://coda.io/apis/v1/docs/{os.environ['CODA_DOC_ID']}/tables/{os.environ['CODA_PAIRINGS_TABLE_ID']}/rows"
	res = requests.get(url, headers=headers, params={"valueFormat": "rich", "limit": 500})
	res.raise_for_status()
	items = res.json().get("items", [])
	lo, hi = sorted((p1, p2))
	pc1 = os.environ["CODA_PERSON_1_COL_ID"]
	pc2 = os.environ["CODA_PERSON_2_COL_ID"]
	count = 0
	for it in items:
		vals = it.get("values", {})
		v1 = _extract_row_id(vals.get(pc1))
		v2 = _extract_row_id(vals.get(pc2))
		if v1 == lo and v2 == hi:
			count += 1
	assert count == 1


@pytest.mark.skipif(skip_integration, reason=skip_reason)
def test_coda_upsert_enforces_sorted_order():
	store = PairStore()
	p1 = os.environ["CODA_TEST_PERSON1_ID"]
	p2 = os.environ["CODA_TEST_PERSON2_ID"]
	_cleanup_pair(p1, p2)
	# Intentionally reversed input
	store.add_pairs([(p2, p1)])

	# Fetch and verify Person 1 column is lexicographically lower than Person 2
	headers = {"Authorization": f"Bearer {os.environ['CODA_API_TOKEN']}"}
	url = f"https://coda.io/apis/v1/docs/{os.environ['CODA_DOC_ID']}/tables/{os.environ['CODA_PAIRINGS_TABLE_ID']}/rows"
	pc1 = os.environ["CODA_PERSON_1_COL_ID"]
	pc2 = os.environ["CODA_PERSON_2_COL_ID"]
	lo, hi = sorted((p1, p2))

	for _ in range(10):
		res = requests.get(url, headers=headers, params={"valueFormat": "rich", "limit": 200})
		res.raise_for_status()
		items = res.json().get("items", [])
		found_sorted = False
		found_reversed = False
		for it in items:
			vals = it.get("values", {})
			v1 = _extract_row_id(vals.get(pc1))
			v2 = _extract_row_id(vals.get(pc2))
			if v1 == lo and v2 == hi:
				found_sorted = True
			if v1 == hi and v2 == lo:
				found_reversed = True
		if found_sorted and not found_reversed:
			break
		time.sleep(1)

	assert found_sorted is True
	assert found_reversed is False


@pytest.mark.skipif(
	any(os.environ.get(k) in (None, "") for k in required_envs + ["CODA_TEST_PERSON3_ID", "CODA_TEST_PERSON4_ID"]),
	reason="Missing env vars for multi-row integration test",
)
def test_coda_upsert_multiple_rows():
	store = PairStore()
	p1 = os.environ["CODA_TEST_PERSON1_ID"]
	p2 = os.environ["CODA_TEST_PERSON2_ID"]
	p3 = os.environ["CODA_TEST_PERSON3_ID"]
	p4 = os.environ["CODA_TEST_PERSON4_ID"]
	store.add_pairs([(p1, p2), (p3, p4)])

	# Verify both pairs exist exactly once, allow for async mutation to apply
	headers = {"Authorization": f"Bearer {os.environ['CODA_API_TOKEN']}"}
	url = f"https://coda.io/apis/v1/docs/{os.environ['CODA_DOC_ID']}/tables/{os.environ['CODA_PAIRINGS_TABLE_ID']}/rows"
	pc1 = os.environ["CODA_PERSON_1_COL_ID"]
	pc2 = os.environ["CODA_PERSON_2_COL_ID"]

	def fetch_items():
		res = requests.get(url, headers=headers, params={"valueFormat": "rich", "limit": 500})
		res.raise_for_status()
		return res.json().get("items", [])

	def count_pair(items, a, b):
		lo, hi = sorted((a, b))
		c = 0
		for it in items:
			vals = it.get("values", {})
			v1 = _extract_row_id(vals.get(pc1))
			v2 = _extract_row_id(vals.get(pc2))
			if v1 == lo and v2 == hi:
				c += 1
		return c

	for _ in range(10):
		items = fetch_items()
		if count_pair(items, p1, p2) == 1 and count_pair(items, p3, p4) == 1:
			break
		time.sleep(1)

	items = fetch_items()
	assert count_pair(items, p1, p2) == 1
	assert count_pair(items, p3, p4) == 1


