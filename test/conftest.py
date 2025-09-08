import os
import sys

from dotenv import load_dotenv
load_dotenv()


def pytest_configure(config):
	config.addinivalue_line("markers", "coda_destructive: marks destructive Coda tests")

def pytest_collection_modifyitems(config, items):
	"""Prompt before running destructive Coda integration tests.

	Runs at collection time so the warning appears before pytest prints test node ids.
	If the user does not confirm, the tests are deselected.
	"""
	integration_items = [it for it in items if it.get_closest_marker("coda_destructive")]
	if not integration_items:
		return

	# Avoid hanging in non-interactive environments (e.g. CI)
	if not sys.stdin or not getattr(sys.stdin, "isatty", lambda: False)():
		config.hook.pytest_deselected(items=integration_items)
		for it in integration_items:
			items.remove(it)
		print("\n[skip] Non-interactive session; skipping destructive Coda integration tests")
		return

	print("\n=== WARNING: Destructive Coda Integration Tests ===")
	print("These tests will upsert and delete rows in your Coda doc and may take several minutes.")
	doc = os.environ.get("CODA_DOC_ID", "")
	table = os.environ.get("CODA_PAIRINGS_TABLE_ID", "")
	pc1 = os.environ.get("CODA_PERSON_1_ID_COL_ID", "")
	pc2 = os.environ.get("CODA_PERSON_2_ID_COL_ID", "")
	if any([doc, table, pc1, pc2]):
		print(f"Targets: DOC={doc} TABLE={table} PERSON_1_COL={pc1} PERSON_2_COL={pc2}")
	try:
		resp = input("Type EXACTLY 'PROCEED' to run them, anything else to skip: ").strip()
	except EOFError:
		resp = ""
	if resp != "PROCEED":
		config.hook.pytest_deselected(items=integration_items)
		for it in integration_items:
			items.remove(it)
		print("[skip] User did not confirm; deselected Coda integration tests.")
		return


