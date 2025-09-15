import os
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

pinecone = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

INDEX_NAME = "matchmaker-interests-3072"
MODEL_DIMENSION = 3072 # gemini-embedding-001

if not pinecone.has_index(INDEX_NAME):
	print("Index does not exist. Creating...")
	pinecone.create_index(
		name=INDEX_NAME,
		vector_type="dense",
		dimension=MODEL_DIMENSION,
		metric="cosine",
		spec=ServerlessSpec(cloud="aws", region="us-east-1"),
	)
	print("Initialized vector db!")
else:
	print("Already initialized vector db.")
