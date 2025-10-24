from .coda_client import CodaClient

def verify_email(person_id: str, verification_id: str):
	coda = CodaClient()

	return coda.verify_email(person_id=person_id, verification_id=verification_id)
