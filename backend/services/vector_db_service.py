import chromadb


client = chromadb.PersistentClient(path="vector_db")

collection = client.get_or_create_collection(
    name="repo_embeddings"
)