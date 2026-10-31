"""
backend/services/vector_db_service.py

ChromaDB persistent client using cosine similarity.
Collection is initialised once at import time and shared across the app.
"""
import chromadb
from chromadb.config import Settings as ChromaSettings

# Persist the vector DB inside the project directory
client = chromadb.PersistentClient(
    path="vector_db",
    settings=ChromaSettings(anonymized_telemetry=False),
)

collection = client.get_or_create_collection(
    name="repo_embeddings",
    metadata={"hnsw:space": "cosine"},   # cosine similarity ↑ better recall
)