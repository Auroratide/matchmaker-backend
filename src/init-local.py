from pinecone import ServerlessSpec
from pinecone.grpc import PineconeGRPC, GRPCClientConfig
from ollama import Client

ollama = Client(
	host="http://localhost:11434"
)

pinecone = PineconeGRPC(
	api_key="pclocal",
	host="http://localhost:5080"
)

MODEL = "nomic-embed-text"
MODEL_DIM = 768
INDEX_NAME = "matchmaking-interests"

if not pinecone.has_index(INDEX_NAME):
	print("Index does not exist. Creating...")
	pinecone.create_index(
		name=INDEX_NAME,
		vector_type="dense",
		dimension=MODEL_DIM,
		metric="cosine",
		spec=ServerlessSpec(cloud="aws", region="us-east-1"),
	)

index_host = pinecone.describe_index(name=INDEX_NAME).host
index = pinecone.Index(host=index_host, grpc_config=GRPCClientConfig(secure=False))

def insert(index, text, id, pastPairings):
	embedding = ollama.embed(model=MODEL, input=text)

	index.upsert(
		vectors=[ {
			"id": id,
			"values": list(embedding.embeddings[0]),
			"metadata": {
				"message": text,
				"subscribed": True,
				"pastPairings": pastPairings,
			},
		} ],
	)

insert(index, "Mercury is the first planet from the sun. It is a rocky planet.", "mercury", ["venus"])
insert(index, "Venus is the second planet from the sun.  It is a rocky planet.", "venus", ["mercury", "earth"])
insert(index, "Earth is the third planet from the sun.  It is a rocky planet.", "earth", ["mars", "venus"])
insert(index, "Mars is the fourth planet from the sun.  It is a rocky planet.", "mars", ["earth"])
insert(index, "Jupiter is the fifth planet from the sun.  It is a gas giant.", "jupiter", [])
insert(index, "Saturn is the sixth planet from the sun.  It is a gas giant.", "saturn", [])
insert(index, "Uranus is the seventh planet from the sun.  It is a gas giant.", "uranus", [])
insert(index, "Neptune is the eighth planet from the sun.  It is a gas giant.", "neptune", [])
insert(index, "Pluto is a dwarf planet.", "pluto", [])
insert(index, "Eris is a dwarf planet.", "eris", [])

print("Initialized vector db")
