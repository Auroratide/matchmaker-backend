import os
from typing import Iterable, Set, Tuple, Dict, Any

import requests


def _normalize_pair(a: str, b: str) -> Tuple[str, str]:
	"""Return a stable, order-independent pair key."""
	return tuple(sorted((a, b)))  # type: ignore[return-value]


class PairStore:
	"""Load existing pairs from Pinecone and upsert new pairs to Coda.

	- Expects Pinecone match objects with attributes: id: str and metadata: dict
	  containing key 'pastPairings' (list[str]).
	- Builds Coda row payloads using provided column IDs and sends a single
	  bulk upsert request keyed on (Person 1 ID, Person 2 ID).
	"""

	def __init__(self) -> None:
		self._coda_token = os.environ.get("CODA_API_TOKEN")
		self._coda_doc_id = os.environ.get("CODA_DOC_ID")
		self._coda_pairings_table_id = os.environ.get("CODA_PAIRINGS_TABLE_ID")
		self._col_person1_lookup = os.environ.get("CODA_PERSON_1_COL_ID")
		self._col_person2_lookup = os.environ.get("CODA_PERSON_2_COL_ID")
		self._col_person1_id = os.environ.get("CODA_PERSON_1_ID_COL_ID")
		self._col_person2_id = os.environ.get("CODA_PERSON_2_ID_COL_ID")
		self._col_send_email = os.environ.get("CODA_SEND_EMAIL_COL_ID")


	def load_pairs(self, vectors) -> Set[Tuple[str, str]]:
		"""Return normalized pairs drawn from vectors' metadata['pastPairings']."""
		existing_pairs: Set[Tuple[str, str]] = set()
		for vec in vectors:
			past = vec.metadata["pastPairings"] or []
			for partner_id in past:
				existing_pairs.add(_normalize_pair(vec.id, partner_id))
		return existing_pairs

	def add_pairs(self, pairs: Iterable[Tuple[str, str]]) -> int:
		"""Bulk upsert pairs to Coda; returns number of rows attempted.

		Builds rows with lookup cells set via {"rowId": id} and uses
		(Person 1 ID, Person 2 ID) as the upsert key.
		"""
		rows: list[dict[str, Any]] = []
		for a, b in pairs:
			lo, hi = sorted((a, b))
			cells = [
				{"column": self._col_person1_lookup, "value": lo},
				{"column": self._col_person2_lookup, "value": hi},
				{"column": self._col_send_email, "value": True},
			]
			rows.append({"cells": cells})

		if not rows:
			return 0

		payload = {"rows": rows, "keyColumns": [self._col_person1_lookup, self._col_person2_lookup]}
		url = f"https://coda.io/apis/v1/docs/{self._coda_doc_id}/tables/{self._coda_pairings_table_id}/rows"
		resp = requests.post(url, headers=self._coda_headers(), json=payload, timeout=60)
		if resp.status_code != 202:
			raise RuntimeError(f"Coda upsert failed: {resp.status_code} {resp.text}")
		return len(rows)

	def _coda_headers(self) -> Dict[str, str]:
		return {
			"Authorization": f"Bearer {self._coda_token}",
			"Content-Type": "application/json",
		}